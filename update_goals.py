"""
Copa do Mundo 2026 — Atualizador de Gols
Busca gols da ESPN e gera o index.html atualizado.
Rodado automaticamente pelo GitHub Actions a cada 12 horas.
"""
import urllib.request
import json
import datetime
import time
import sys

BASE_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world"

PAISES = {
    'MEX': 'México',         'RSA': 'África do Sul',  'KOR': 'Coreia do Sul',
    'CZE': 'Tchequia',       'CAN': 'Canadá',          'BIH': 'Bósnia-Herzegovina',
    'USA': 'EUA',            'PAR': 'Paraguai',         'QAT': 'Catar',
    'SUI': 'Suíça',          'BRA': 'Brasil',           'MAR': 'Marrocos',
    'HAI': 'Haiti',          'SCO': 'Escócia',          'AUS': 'Austrália',
    'TUR': 'Turquia',        'GER': 'Alemanha',         'CUW': 'Curaçao',
    'ECU': 'Equador',        'CIV': 'Costa do Marfim',  'NED': 'P. Baixos',
    'JPN': 'Japão',          'TUN': 'Tunísia',          'SWE': 'Suécia',
    'ESP': 'Espanha',        'CPV': 'Cabo Verde',        'BEL': 'Bélgica',
    'EGY': 'Egito',          'URU': 'Uruguai',           'KSA': 'Arábia Saudita',
    'IRN': 'Irã',            'NZL': 'Nova Zelândia',     'FRA': 'França',
    'SEN': 'Senegal',        'NOR': 'Noruega',           'IRQ': 'Iraque',
    'ARG': 'Argentina',      'ALG': 'Argélia',           'AUT': 'Áustria',
    'JOR': 'Jordânia',       'POR': 'Portugal',          'CGO': 'RD Congo',
    'COD': 'RD Congo',       'ENG': 'Inglaterra',        'CRO': 'Croácia',
    'GHA': 'Gana',           'PAN': 'Panamá',            'UZB': 'Uzbequistão',
    'COL': 'Colômbia',       'HON': 'Honduras',          'SLV': 'El Salvador',
    'NGA': 'Nigéria',        'CMR': 'Camarões',          'MLI': 'Mali',
    'DEN': 'Dinamarca',      'POL': 'Polônia',           'SVK': 'Eslováquia',
    'ROM': 'Romênia',        'SRB': 'Sérvia',            'HUN': 'Hungria',
    'WAL': 'País de Gales',  'GRE': 'Grécia',
}

# Todas as datas da Copa (fase de grupos + eliminatórias)
DATAS = [
    '20260611','20260612','20260613','20260614','20260615',
    '20260616','20260617','20260618','20260619','20260620',
    '20260621','20260622','20260623','20260624','20260625',
    '20260626','20260627','20260628','20260629','20260630',
    '20260701','20260702','20260703','20260704','20260705',
    '20260706','20260707','20260708','20260709','20260710',
    '20260711','20260712','20260713','20260714','20260715',
    '20260716','20260717','20260718','20260719',
]


def fetch_json(url, timeout=20):
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; Copa2026Bot/1.0)',
        'Accept': 'application/json',
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8'))


def traduzir_partida(short_name):
    """Converte 'RSA @ MEX' → 'México x África do Sul'"""
    parts = (short_name or '').split(' @ ')
    if len(parts) != 2:
        return short_name
    away, home = parts
    return f"{PAISES.get(home, home)} x {PAISES.get(away, away)}"


def calcular_fase(data_utc):
    dt = datetime.datetime.fromisoformat(data_utc.replace('Z', '+00:00'))
    thresholds = [
        (datetime.datetime(2026, 6, 18, 3, 0, tzinfo=datetime.timezone.utc), 'Rodada 1'),
        (datetime.datetime(2026, 6, 23, 3, 0, tzinfo=datetime.timezone.utc), 'Rodada 2'),
        (datetime.datetime(2026, 6, 28, 3, 0, tzinfo=datetime.timezone.utc), 'Rodada 3'),
        (datetime.datetime(2026, 7, 5,  3, 0, tzinfo=datetime.timezone.utc), 'Oitavas'),
        (datetime.datetime(2026, 7, 9,  3, 0, tzinfo=datetime.timezone.utc), 'Quartas'),
        (datetime.datetime(2026, 7, 13, 3, 0, tzinfo=datetime.timezone.utc), 'Semifinal'),
        (datetime.datetime(2026, 7, 15, 3, 0, tzinfo=datetime.timezone.utc), 'Terceiro Lugar'),
    ]
    for cutoff, label in thresholds:
        if dt < cutoff:
            return label
    return 'Final'


def traduzir_tipo(text):
    t = (text or '').lower()
    if 'own' in t or 'contra' in t:
        return 'Gol Contra'
    if 'penalty' in t or 'pen' in t:
        return 'Pênalti'
    return 'Gol'


def get_all_goals():
    goals = []
    seen_events = set()

    for date_str in DATAS:
        try:
            print(f"  Buscando {date_str}...", end=' ')
            scoreboard = fetch_json(f"{BASE_URL}/scoreboard?dates={date_str}")
            events = scoreboard.get('events', [])
            print(f"{len(events)} jogo(s)")

            for event in events:
                eid = event['id']
                if eid in seen_events:
                    continue
                seen_events.add(eid)

                comp = event['competitions'][0]
                state = comp['status']['type']['state']
                if state not in ('in', 'post'):
                    continue  # jogo ainda não ocorreu

                partida = traduzir_partida(event.get('shortName', ''))
                data_utc = event['date']
                fase = calcular_fase(data_utc)

                # Converte para horário de Brasília (UTC-3)
                dt = datetime.datetime.fromisoformat(data_utc.replace('Z', '+00:00'))
                dt_br = dt - datetime.timedelta(hours=3)
                data_br = dt_br.strftime('%d/%m/%Y')

                # Mapa de times para lookup por ID
                team_map = {
                    c['team']['id']: c['team']
                    for c in comp.get('competitors', [])
                }

                # Busca gols no endpoint de summary
                try:
                    time.sleep(0.5)  # respeita rate limit da ESPN
                    summary = fetch_json(f"{BASE_URL}/summary?event={eid}")

                    for play in summary.get('scoringPlays', []):
                        tipo_text = play.get('type', {}).get('text', 'Goal')
                        tipo_lower = tipo_text.lower()

                        if 'goal' not in tipo_lower and 'penalty' not in tipo_lower:
                            continue

                        team_id = play.get('team', {}).get('id', '')
                        team = team_map.get(team_id, {})
                        team_abbr = team.get('abbreviation', '')
                        pais = PAISES.get(team_abbr) or team.get('displayName', '?')

                        athletes = play.get('athletesInvolved', [])
                        jogador = athletes[0].get('displayName', '?') if athletes else '?'
                        minuto = play.get('clock', {}).get('displayValue', '?')
                        tipo = traduzir_tipo(tipo_text)

                        goals.append({
                            'partida': partida,
                            'data': data_br,
                            'pais': pais,
                            'jogador': jogador,
                            'minuto': minuto,
                            'fase': fase,
                            'tipo': tipo,
                            'sort_key': (data_utc, minuto),
                        })

                except Exception as e:
                    print(f"    ⚠ summary {eid} ({partida}): {e}")

        except Exception as e:
            print(f"  ⚠ scoreboard {date_str}: {e}")

    return goals


# Cores por fase
FASE_CORES = {
    'Rodada 1':      ('#e8f5e9', '#1b5e20'),
    'Rodada 2':      ('#e3f2fd', '#0d47a1'),
    'Rodada 3':      ('#fff8e1', '#f57f17'),
    'Oitavas':       ('#fce4ec', '#880e4f'),
    'Quartas':       ('#f3e5f5', '#4a148c'),
    'Semifinal':     ('#ffe0b2', '#bf360c'),
    'Terceiro Lugar':('#efebe9', '#3e2723'),
    'Final':         ('#ffecb3', '#ff6f00'),
}

TIPO_BADGE = {
    'Gol':         ('⚽', '#43a047', '#fff'),
    'Pênalti':     ('🎯', '#1565c0', '#fff'),
    'Gol Contra':  ('😬', '#b71c1c', '#fff'),
}


def gerar_html(goals):
    now_utc = datetime.datetime.utcnow()
    now_br = now_utc - datetime.timedelta(hours=3)
    ts = now_br.strftime('%d/%m/%Y %H:%M')

    total = len(goals)

    # Conta gols por país
    ranking = {}
    for g in goals:
        if g['tipo'] != 'Gol Contra':
            ranking[g['pais']] = ranking.get(g['pais'], 0) + 1
    top5 = sorted(ranking.items(), key=lambda x: -x[1])[:5]

    top5_html = ''.join(
        f'<div class="top-item"><span class="top-rank">#{i+1}</span>'
        f'<span class="top-pais">{p}</span>'
        f'<span class="top-gols">{n} ⚽</span></div>'
        for i, (p, n) in enumerate(top5)
    )

    rows = ''
    for g in goals:
        bg, fg = FASE_CORES.get(g['fase'], ('#fff', '#000'))
        emoji, badge_bg, badge_fg = TIPO_BADGE.get(g['tipo'], ('⚽', '#43a047', '#fff'))
        rows += f'''
      <tr>
        <td class="td-partida">{g["partida"]}</td>
        <td class="td-data">{g["data"]}</td>
        <td class="td-pais">{g["pais"]}</td>
        <td class="td-jogador"><strong>{g["jogador"]}</strong></td>
        <td class="td-min">{g["minuto"]}</td>
        <td><span class="fase-badge" style="background:{bg};color:{fg}">{g["fase"]}</span></td>
        <td><span class="tipo-badge" style="background:{badge_bg};color:{badge_fg}">{emoji} {g["tipo"]}</span></td>
      </tr>'''

    return f'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>⚽ Copa do Mundo 2026 — Gols</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Segoe UI', Arial, sans-serif;
      background: #0d1117;
      color: #e6edf3;
      min-height: 100vh;
    }}
    header {{
      background: linear-gradient(135deg, #1a3c5e 0%, #0f2e1a 100%);
      padding: 24px 32px;
      border-bottom: 3px solid #238636;
    }}
    header h1 {{ font-size: 1.8rem; font-weight: 700; }}
    header h1 span {{ color: #3fb950; }}
    .meta {{
      margin-top: 6px;
      font-size: 0.85rem;
      color: #8b949e;
    }}
    .container {{ max-width: 1200px; margin: 0 auto; padding: 24px 16px; }}
    .stats-row {{
      display: flex;
      gap: 16px;
      margin-bottom: 24px;
      flex-wrap: wrap;
    }}
    .stat-card {{
      background: #161b22;
      border: 1px solid #30363d;
      border-radius: 8px;
      padding: 16px 24px;
      flex: 1;
      min-width: 140px;
      text-align: center;
    }}
    .stat-card .num {{ font-size: 2rem; font-weight: 700; color: #3fb950; }}
    .stat-card .label {{ font-size: 0.8rem; color: #8b949e; margin-top: 4px; }}
    .top-scorers {{
      background: #161b22;
      border: 1px solid #30363d;
      border-radius: 8px;
      padding: 16px;
      margin-bottom: 24px;
    }}
    .top-scorers h3 {{ font-size: 0.9rem; color: #8b949e; margin-bottom: 12px; }}
    .top-item {{
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 6px 0;
      border-bottom: 1px solid #21262d;
    }}
    .top-item:last-child {{ border-bottom: none; }}
    .top-rank {{ font-weight: 700; color: #f0c93a; width: 28px; }}
    .top-pais {{ flex: 1; font-size: 0.9rem; }}
    .top-gols {{ font-size: 0.85rem; color: #3fb950; font-weight: 600; }}
    .table-wrap {{
      overflow-x: auto;
      border-radius: 8px;
      border: 1px solid #30363d;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.88rem;
    }}
    thead th {{
      background: #161b22;
      color: #8b949e;
      font-weight: 600;
      padding: 10px 14px;
      text-align: left;
      white-space: nowrap;
      border-bottom: 2px solid #30363d;
    }}
    tbody tr {{ background: #0d1117; transition: background 0.15s; }}
    tbody tr:hover {{ background: #161b22; }}
    tbody tr:nth-child(even) {{ background: #111820; }}
    tbody tr:nth-child(even):hover {{ background: #1a2332; }}
    td {{
      padding: 9px 14px;
      border-bottom: 1px solid #21262d;
      vertical-align: middle;
    }}
    .td-partida {{ font-weight: 500; min-width: 180px; }}
    .td-data {{ white-space: nowrap; color: #8b949e; }}
    .td-pais {{ white-space: nowrap; }}
    .td-jogador {{ min-width: 160px; }}
    .td-min {{ text-align: center; color: #8b949e; font-variant-numeric: tabular-nums; }}
    .fase-badge {{
      display: inline-block;
      padding: 2px 8px;
      border-radius: 12px;
      font-size: 0.78rem;
      font-weight: 600;
      white-space: nowrap;
    }}
    .tipo-badge {{
      display: inline-block;
      padding: 2px 8px;
      border-radius: 12px;
      font-size: 0.78rem;
      font-weight: 600;
      white-space: nowrap;
    }}
    .filter-bar {{
      display: flex;
      gap: 10px;
      margin-bottom: 16px;
      flex-wrap: wrap;
    }}
    .filter-bar input, .filter-bar select {{
      background: #161b22;
      border: 1px solid #30363d;
      color: #e6edf3;
      border-radius: 6px;
      padding: 8px 12px;
      font-size: 0.88rem;
      outline: none;
    }}
    .filter-bar input:focus, .filter-bar select:focus {{
      border-color: #3fb950;
    }}
    .filter-bar input {{ flex: 1; min-width: 200px; }}
    .empty {{ text-align: center; padding: 48px; color: #8b949e; }}
    footer {{
      text-align: center;
      padding: 20px;
      color: #484f58;
      font-size: 0.8rem;
      border-top: 1px solid #21262d;
      margin-top: 32px;
    }}
    @media (max-width: 600px) {{
      .td-partida, .td-jogador {{ min-width: 120px; }}
      header h1 {{ font-size: 1.3rem; }}
    }}
  </style>
</head>
<body>

<header>
  <h1>⚽ Copa do Mundo 2026 — <span>Todos os Gols</span></h1>
  <p class="meta">Atualizado automaticamente · Última atualização: <strong id="ts">{ts} (Brasília)</strong></p>
</header>

<div class="container">

  <div class="stats-row">
    <div class="stat-card">
      <div class="num" id="total-gols">{total}</div>
      <div class="label">Gols no Torneio</div>
    </div>
    <div class="stat-card">
      <div class="num">{len(set(g["jogador"] for g in goals if g["jogador"] != "?"))}</div>
      <div class="label">Marcadores</div>
    </div>
    <div class="stat-card">
      <div class="num">{len(set(g["partida"] for g in goals))}</div>
      <div class="label">Jogos com Gols</div>
    </div>
    <div class="top-scorers" style="flex:2;min-width:220px">
      <h3>🏆 Top 5 seleções artilheiras</h3>
      {top5_html}
    </div>
  </div>

  <div class="filter-bar">
    <input type="text" id="busca" placeholder="🔍  Buscar jogador, partida ou país..." oninput="filtrar()">
    <select id="fase-filtro" onchange="filtrar()">
      <option value="">Todas as fases</option>
      <option>Rodada 1</option>
      <option>Rodada 2</option>
      <option>Rodada 3</option>
      <option>Oitavas</option>
      <option>Quartas</option>
      <option>Semifinal</option>
      <option>Terceiro Lugar</option>
      <option>Final</option>
    </select>
    <select id="tipo-filtro" onchange="filtrar()">
      <option value="">Todos os tipos</option>
      <option>Gol</option>
      <option>Pênalti</option>
      <option>Gol Contra</option>
    </select>
  </div>

  <div class="table-wrap">
    <table id="tabela-gols">
      <thead>
        <tr>
          <th>Partida</th>
          <th>Data</th>
          <th>País</th>
          <th>Jogador</th>
          <th>Min.</th>
          <th>Fase</th>
          <th>Tipo</th>
        </tr>
      </thead>
      <tbody id="tbody">
        {rows if rows else '<tr><td colspan="7" class="empty">Nenhum gol registrado ainda.</td></tr>'}
      </tbody>
    </table>
  </div>

  <p id="contador" style="margin-top:10px;font-size:0.82rem;color:#484f58"></p>

</div>

<footer>
  Dados: ESPN API · Atualização automática a cada 12h via GitHub Actions · Copa do Mundo 2026
</footer>

<script>
  function filtrar() {{
    const busca = document.getElementById('busca').value.toLowerCase();
    const fase  = document.getElementById('fase-filtro').value;
    const tipo  = document.getElementById('tipo-filtro').value;
    const linhas = document.querySelectorAll('#tbody tr');
    let vis = 0;
    linhas.forEach(tr => {{
      const txt = tr.textContent.toLowerCase();
      const ok = txt.includes(busca)
        && (!fase || txt.includes(fase.toLowerCase()))
        && (!tipo || txt.includes(tipo.toLowerCase()));
      tr.style.display = ok ? '' : 'none';
      if (ok) vis++;
    }});
    document.getElementById('contador').textContent =
      vis < linhas.length ? `Mostrando ${{vis}} de ${{linhas.length}} gols` : '';
  }}
</script>

</body>
</html>'''


if __name__ == '__main__':
    print('⚽ Copa do Mundo 2026 — Atualizador de Gols')
    print('=' * 50)
    print('Buscando dados da ESPN...')

    goals = get_all_goals()
    print(f'\n✅ Total de gols encontrados: {len(goals)}')

    # Ordena por data e minuto
    goals.sort(key=lambda g: g['sort_key'])

    html = gerar_html(goals)
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html)

    print('✅ index.html gerado com sucesso!')
    sys.exit(0)
