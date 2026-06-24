"""
Copa do Mundo 2026 — base limpa de gols

Gera uma fonte simples para Excel, Power Query e Power BI:
- gols.csv  -> fonte principal para conexão via Web
- index.html -> visualização simples no GitHub Pages

Cada linha do CSV representa 1 gol identificado na fonte de dados.
Campos finais: nome_jogador, pais, data_jogo, hora_jogo

A coluna pais indica a seleção favorecida pelo gol. Em caso de gol contra,
o jogador continua sendo o autor do gol contra, mas o pais será a seleção
que recebeu o gol no placar.
"""
from __future__ import annotations

import csv
import datetime as dt
import html
import json
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

BASE_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world"
BR_TZ = ZoneInfo("America/Sao_Paulo")
UTC = dt.timezone.utc

START_DATE = dt.date(2026, 6, 11)
END_DATE = dt.date(2026, 7, 19)

OUTPUT_CSV = Path("gols.csv")
OUTPUT_HTML = Path("index.html")
OUTPUT_JSON = Path("gols.json")

CSV_FIELDS = ["nome_jogador", "pais", "data_jogo", "hora_jogo"]

TEAM_NAMES = {
    "MEX": "México",
    "RSA": "África do Sul",
    "KOR": "Coreia do Sul",
    "CZE": "Tchequia",
    "CAN": "Canadá",
    "BIH": "Bósnia-Herzegovina",
    "USA": "EUA",
    "PAR": "Paraguai",
    "QAT": "Catar",
    "SUI": "Suíça",
    "BRA": "Brasil",
    "MAR": "Marrocos",
    "HAI": "Haiti",
    "HTI": "Haiti",
    "SCO": "Escócia",
    "AUS": "Austrália",
    "TUR": "Turquia",
    "GER": "Alemanha",
    "CUW": "Curaçao",
    "ECU": "Equador",
    "CIV": "Costa do Marfim",
    "NED": "Países Baixos",
    "JPN": "Japão",
    "TUN": "Tunísia",
    "SWE": "Suécia",
    "ESP": "Espanha",
    "CPV": "Cabo Verde",
    "BEL": "Bélgica",
    "EGY": "Egito",
    "URU": "Uruguai",
    "KSA": "Arábia Saudita",
    "IRN": "Irã",
    "IRI": "Irã",
    "NZL": "Nova Zelândia",
    "FRA": "França",
    "SEN": "Senegal",
    "NOR": "Noruega",
    "IRQ": "Iraque",
    "ARG": "Argentina",
    "ALG": "Argélia",
    "DZA": "Argélia",
    "AUT": "Áustria",
    "JOR": "Jordânia",
    "POR": "Portugal",
    "CGO": "RD Congo",
    "COD": "RD Congo",
    "ENG": "Inglaterra",
    "CRO": "Croácia",
    "GHA": "Gana",
    "PAN": "Panamá",
    "UZB": "Uzbequistão",
    "COL": "Colômbia",
    "HON": "Honduras",
    "SLV": "El Salvador",
    "NGA": "Nigéria",
    "CMR": "Camarões",
    "MLI": "Mali",
    "DEN": "Dinamarca",
    "POL": "Polônia",
    "SVK": "Eslováquia",
    "ROM": "Romênia",
    "SRB": "Sérvia",
    "HUN": "Hungria",
    "WAL": "País de Gales",
    "GRE": "Grécia",
}


def daterange(start: dt.date, end: dt.date):
    current = start
    while current <= end:
        yield current
        current += dt.timedelta(days=1)


def fetch_json(url: str, timeout: int = 25, retries: int = 3) -> dict[str, Any]:
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; Copa2026Dados/1.0)",
        "Accept": "application/json",
    }
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            request = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001 - mantém o Actions robusto e registra o erro
            last_error = exc
            if attempt < retries:
                time.sleep(1.2 * attempt)
    raise RuntimeError(f"Falha ao buscar {url}: {last_error}")


def parse_utc_datetime(value: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def team_display_name(team: dict[str, Any] | None) -> str:
    if not team:
        return "Não informado"
    abbr = (team.get("abbreviation") or team.get("abbr") or "").upper()
    return TEAM_NAMES.get(abbr) or team.get("displayName") or team.get("shortDisplayName") or abbr or "Não informado"


def get_team_maps(competition: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], list[str]]:
    team_by_id: dict[str, dict[str, Any]] = {}
    team_ids: list[str] = []
    for competitor in competition.get("competitors", []):
        team = competitor.get("team") or {}
        team_id = str(team.get("id") or "")
        if team_id:
            team_by_id[team_id] = team
            team_ids.append(team_id)
    return team_by_id, team_ids


def play_team_id(play: dict[str, Any]) -> str:
    team = play.get("team") or {}
    return str(team.get("id") or play.get("teamId") or "")


def athlete_from_play(play: dict[str, Any]) -> tuple[str | None, dict[str, Any] | None]:
    possible_lists = [
        play.get("athletesInvolved"),
        play.get("participants"),
        play.get("athletes"),
    ]

    for items in possible_lists:
        if not items:
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            athlete = item.get("athlete") if isinstance(item.get("athlete"), dict) else item
            name = athlete.get("displayName") or athlete.get("name") or item.get("displayName") or item.get("name")
            if name and name != "?":
                return str(name).strip(), athlete

    athlete = play.get("athlete")
    if isinstance(athlete, dict):
        name = athlete.get("displayName") or athlete.get("name")
        if name and name != "?":
            return str(name).strip(), athlete

    return None, None


def athlete_team_id(athlete: dict[str, Any] | None) -> str:
    if not athlete:
        return ""

    team = athlete.get("team")
    if isinstance(team, dict):
        team_id = team.get("id") or team.get("teamId")
        if team_id:
            return str(team_id)

    for key in ("teamId", "teamID", "team_id"):
        if athlete.get(key):
            return str(athlete.get(key))

    return ""


def is_own_goal(play: dict[str, Any]) -> bool:
    text = " ".join(
        str(value or "")
        for value in [
            play.get("text"),
            play.get("shortText"),
            (play.get("type") or {}).get("text"),
        ]
    ).lower()
    return bool(play.get("ownGoal")) or "own goal" in text or "gol contra" in text


def is_goal_play(play: dict[str, Any]) -> bool:
    text = " ".join(
        str(value or "")
        for value in [
            play.get("text"),
            play.get("shortText"),
            (play.get("type") or {}).get("text"),
        ]
    ).lower()

    # Pênaltis de disputa não contam como gols oficiais da partida.
    if "shootout" in text or "penalty shootout" in text:
        return False

    if play.get("scoringPlay") is True:
        return True

    # Alguns endpoints não enviam scoringPlay, mas enviam o tipo textual.
    return "goal" in text or "penalty - scored" in text


def collect_scoring_plays(event_id: str, competition: dict[str, Any]) -> list[dict[str, Any]]:
    plays: list[dict[str, Any]] = []

    inline_details = competition.get("details") or []
    plays.extend([play for play in inline_details if isinstance(play, dict) and is_goal_play(play)])

    # O summary costuma trazer dados mais completos de atletas. Por isso ele é usado
    # como complemento, mesmo quando o scoreboard já trouxe alguns detalhes.
    try:
        time.sleep(0.25)
        summary = fetch_json(f"{BASE_URL}/summary?event={event_id}")
        for key in ("scoringPlays", "plays"):
            items = summary.get(key) or []
            plays.extend([play for play in items if isinstance(play, dict) and is_goal_play(play)])
    except Exception as exc:  # noqa: BLE001
        print(f"    ⚠ Não foi possível ler summary do jogo {event_id}: {exc}")

    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for play in plays:
        player_name, _ = athlete_from_play(play)
        key = "|".join(
            [
                str(play.get("id") or play.get("sequenceNumber") or ""),
                str(play_team_id(play)),
                str(player_name or ""),
                str((play.get("clock") or {}).get("displayValue") or play.get("clock") or ""),
                str((play.get("period") or {}).get("number") or play.get("period") or ""),
                str(play.get("text") or play.get("shortText") or ""),
            ]
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(play)

    return unique


def country_favored_by_goal(
    play: dict[str, Any],
    athlete: dict[str, Any] | None,
    team_by_id: dict[str, dict[str, Any]],
    team_ids: list[str],
) -> str:
    """Retorna a seleção favorecida pelo gol.

    Regra de negócio da base:
    - Gol normal: país que marcou o gol.
    - Gol contra: país que ganhou o gol no placar, não o país do jogador.

    Na ESPN, o campo play.team normalmente representa o time que recebeu
    o gol no placar. Isso é exatamente o que queremos para a coluna pais.
    O fallback abaixo cobre casos em que o play.team venha ausente em um
    gol contra: nesse cenário usamos o time adversário do atleta.
    """
    scoring_team_id = play_team_id(play)

    if scoring_team_id and scoring_team_id in team_by_id:
        return team_display_name(team_by_id[scoring_team_id])

    # Fallback para gol contra sem team no lance: se soubermos o time do
    # jogador, o país favorecido é o adversário.
    player_team_id = athlete_team_id(athlete)
    if is_own_goal(play) and player_team_id and len(team_ids) == 2:
        opposite_ids = [team_id for team_id in team_ids if team_id != player_team_id]
        if opposite_ids:
            return team_display_name(team_by_id.get(opposite_ids[0]))

    # Último fallback: se não houver identificação clara do país favorecido,
    # ainda tentamos usar o país do atleta para não perder a linha.
    if player_team_id and player_team_id in team_by_id:
        return team_display_name(team_by_id[player_team_id])

    return "Não informado"


def get_all_goals() -> tuple[list[dict[str, str]], int, int]:
    rows: list[dict[str, str]] = []
    seen_events: set[str] = set()
    successful_scoreboards = 0
    failed_scoreboards = 0

    for current_date in daterange(START_DATE, END_DATE):
        date_param = current_date.strftime("%Y%m%d")
        try:
            print(f"  Buscando agenda de {date_param}...")
            scoreboard = fetch_json(f"{BASE_URL}/scoreboard?dates={date_param}")
            successful_scoreboards += 1
        except Exception as exc:  # noqa: BLE001
            failed_scoreboards += 1
            print(f"  ⚠ Erro ao buscar {date_param}: {exc}")
            continue

        events = scoreboard.get("events") or []
        print(f"    {len(events)} jogo(s) encontrado(s)")

        for event in events:
            event_id = str(event.get("id") or "")
            if not event_id or event_id in seen_events:
                continue
            seen_events.add(event_id)

            competitions = event.get("competitions") or []
            if not competitions:
                continue
            competition = competitions[0]

            status_type = ((competition.get("status") or {}).get("type") or {})
            state = status_type.get("state")
            completed = status_type.get("completed") is True

            # Regra de segurança: não usamos horário estimado para fingir que jogo acabou.
            # Só entram jogos em andamento ou já encerrados pela própria fonte.
            if not (completed or state in {"in", "post"}):
                continue

            kickoff_utc = parse_utc_datetime(str(event.get("date")))
            kickoff_br = kickoff_utc.astimezone(BR_TZ)
            data_jogo = kickoff_br.strftime("%d/%m/%Y")
            hora_jogo = kickoff_br.strftime("%H:%M")

            team_by_id, team_ids = get_team_maps(competition)
            scoring_plays = collect_scoring_plays(event_id, competition)

            for play in scoring_plays:
                player_name, athlete = athlete_from_play(play)

                # Se o nome do jogador ainda não foi publicado pela fonte,
                # pulamos a linha para não criar dado falso.
                if not player_name:
                    continue

                rows.append(
                    {
                        "nome_jogador": player_name,
                        "pais": country_favored_by_goal(play, athlete, team_by_id, team_ids),
                        "data_jogo": data_jogo,
                        "hora_jogo": hora_jogo,
                        "_sort": f"{kickoff_utc.isoformat()}|{len(rows):06d}",
                    }
                )

    rows.sort(key=lambda item: item["_sort"])
    clean_rows = [{field: row[field] for field in CSV_FIELDS} for row in rows]
    return clean_rows, successful_scoreboards, failed_scoreboards


def write_csv(rows: list[dict[str, str]]) -> None:
    # utf-8-sig ajuda o Excel a reconhecer acentos corretamente.
    # O separador ; costuma funcionar melhor em ambientes pt-BR.
    with OUTPUT_CSV.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_FIELDS, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)


def write_json(rows: list[dict[str, str]], updated_at_br: str) -> None:
    payload = {
        "ultima_atualizacao_brasilia": updated_at_br,
        "total_linhas": len(rows),
        "dados": rows,
    }
    OUTPUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_html(rows: list[dict[str, str]], updated_at_br: str) -> None:
    if rows:
        table_rows = "\n".join(
            "<tr>"
            f"<td>{html.escape(row['nome_jogador'])}</td>"
            f"<td>{html.escape(row['pais'])}</td>"
            f"<td>{html.escape(row['data_jogo'])}</td>"
            f"<td>{html.escape(row['hora_jogo'])}</td>"
            "</tr>"
            for row in rows
        )
    else:
        table_rows = '<tr><td colspan="4">Nenhum gol disponível na fonte até o momento.</td></tr>'

    page = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Gols Copa do Mundo 2026</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; color: #111; }}
    h1 {{ font-size: 24px; margin-bottom: 6px; }}
    p {{ margin: 4px 0 16px; }}
    code {{ background: #f2f2f2; padding: 2px 6px; border-radius: 4px; }}
    table {{ border-collapse: collapse; width: 100%; max-width: 1000px; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
    th {{ background: #f6f6f6; }}
    tr:nth-child(even) {{ background: #fafafa; }}
  </style>
</head>
<body>
  <h1>Gols da Copa do Mundo 2026</h1>
  <p>Última atualização: <strong>{html.escape(updated_at_br)} - Horário de Brasília</strong></p>
  <p>Fonte limpa para Power Query / Power BI: <code>gols.csv</code></p>
  <p>Cada linha representa um gol. A coluna pais mostra a seleção favorecida pelo gol. Em gol contra, o jogador é o autor do gol contra, mas o país é quem recebeu o gol no placar.</p>

  <table>
    <thead>
      <tr>
        <th>nome_jogador</th>
        <th>pais</th>
        <th>data_jogo</th>
        <th>hora_jogo</th>
      </tr>
    </thead>
    <tbody>
      {table_rows}
    </tbody>
  </table>
</body>
</html>
"""
    OUTPUT_HTML.write_text(page, encoding="utf-8")


def main() -> int:
    print("⚽ Copa do Mundo 2026 — Atualizador de base limpa")
    print("=" * 60)

    rows, successful_scoreboards, failed_scoreboards = get_all_goals()
    now_br = dt.datetime.now(UTC).astimezone(BR_TZ).strftime("%d/%m/%Y %H:%M")

    # Proteção contra apagar uma base existente por falha total da fonte/API.
    if successful_scoreboards == 0 and OUTPUT_CSV.exists():
        print("⚠ Nenhuma data foi lida com sucesso. Mantendo arquivos atuais para evitar apagar a base.")
        return 0

    write_csv(rows)
    write_json(rows, now_br)
    write_html(rows, now_br)

    print(f"✅ Scoreboards lidos com sucesso: {successful_scoreboards}")
    print(f"⚠ Scoreboards com erro: {failed_scoreboards}")
    print(f"✅ Linhas geradas no {OUTPUT_CSV}: {len(rows)}")
    print(f"✅ {OUTPUT_HTML} atualizado")
    print(f"✅ {OUTPUT_JSON} atualizado")
    return 0


if __name__ == "__main__":
    sys.exit(main())
