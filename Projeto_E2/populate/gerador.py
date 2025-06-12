import random
from datetime import datetime, timedelta
from faker import Faker
from collections import defaultdict

fake = Faker()

# Configuration
random.seed(42)
NUM_AEROPORTOS = 12
NUM_AVIOES = 40
NUM_MODELOS = 3
DIAS_VOOS = 212  # Jan 1 - Jul 31
MAX_VOOS_POR_ROTA = 3
TOTAL_VENDAS = 30000
TOTAL_BILHETES = 90000

# Airplane models
modelos_aviao = [
    ("Boeing 737-800", 162),
    ("Airbus A320", 150),
    ("Embraer E195", 100)
]

# European airports
aeroportos = [
    ("LHR", "Heathrow Airport", "London", "United Kingdom"),
    ("LGW", "Gatwick Airport", "London", "United Kingdom"),
    ("CDG", "Charles de Gaulle Airport", "Paris", "France"),
    ("ORY", "Orly Airport", "Paris", "France"),
    ("FRA", "Frankfurt Airport", "Frankfurt", "Germany"),
    ("AMS", "Amsterdam Airport Schiphol", "Amsterdam", "Netherlands"),
    ("MAD", "Adolfo Suárez Madrid–Barajas Airport", "Madrid", "Spain"),
    ("BCN", "Barcelona–El Prat Airport", "Barcelona", "Spain"),
    ("FCO", "Leonardo da Vinci–Fiumicino Airport", "Rome", "Italy"),
    ("MXP", "Malpensa Airport", "Milan", "Italy"),
    ("IST", "Istanbul Airport", "Istanbul", "Turkey"),
    ("ZRH", "Zürich Airport", "Zürich", "Switzerland")
]

# Generate airplanes
avioes = []
for i in range(1, NUM_AVIOES + 1):
    modelo_idx = random.randint(0, len(modelos_aviao) - 1)
    modelo_nome, capacidade = modelos_aviao[modelo_idx]
    no_serie = f"{modelo_nome.split()[0]}-{i:03d}"
    avioes.append((no_serie, modelo_nome))

# Generate seats
assentos = []
assentos_por_aviao = defaultdict(list)
assentos_classe_por_aviao = defaultdict(lambda: {'first': 0, 'economy': 0})

for no_serie, modelo_nome in avioes:
    capacidade = next(m[1] for m in modelos_aviao if m[0] == modelo_nome)
    num_fileiras_prim_classe = max(2, int((capacidade / 6) * 0.10))
    for fileira in range(1, (capacidade // 6) + 2):
        for letra in ['A', 'B', 'C', 'D', 'E', 'F']:
            lugar = f"{fileira}{letra}"
            prim_classe = fileira <= num_fileiras_prim_classe
            assentos.append((lugar, no_serie, prim_classe))
            assentos_por_aviao[no_serie].append((lugar, prim_classe))
            key = 'first' if prim_classe else 'economy'
            assentos_classe_por_aviao[no_serie][key] += 1

def gerar_voos():
    voos = []
    data_inicio = datetime(2025, 1, 1)
    aviao_horarios = defaultdict(list)
    voo_partida_slots = set()
    voo_chegada_slots = set()
    
    pares_validos = [(a1[0], a2[0]) for a1 in aeroportos for a2 in aeroportos if a1[2] != a2[2] and a1[3] != a2[3]]
    
    for dia in range(DIAS_VOOS):
        data_atual = data_inicio + timedelta(days=dia)
        random.shuffle(pares_validos)
        for orig, dest in pares_validos:
            for _ in range(random.randint(1, MAX_VOOS_POR_ROTA)):
                for _ in range(50):
                    hora = random.randint(6, 21)
                    minute = random.choice([0, 15, 30, 45])
                    hora_partida = data_atual.replace(hour=hora, minute=minute)
                    duracao = timedelta(hours=random.randint(1, 4), minutes=random.randint(0, 59))
                    hora_chegada = hora_partida + duracao
                    
                    if ((hora_partida, orig, dest) in voo_partida_slots or
                        (hora_chegada, orig, dest) in voo_chegada_slots):
                        continue
                    
                    for aviao in random.sample(avioes, len(avioes)):
                        no_serie = aviao[0]
                        conflito = any(not (hora_chegada < hp or hora_partida > hc) for hp, hc in aviao_horarios[no_serie])
                        if not conflito:
                            aviao_horarios[no_serie].append((hora_partida, hora_chegada))
                            voo_partida_slots.add((hora_partida, orig, dest))
                            voo_chegada_slots.add((hora_chegada, orig, dest))
                            voos.append({
                                'no_serie': no_serie,
                                'hora_partida': hora_partida,
                                'hora_chegada': hora_chegada,
                                'orig': orig,
                                'dest': dest,
                                'has_first_class': False,
                                'has_economy_class': False
                            })
                            break
                    else:
                        continue
                    break
    return voos

voos = gerar_voos()

def gerar_vendas_bilhetes():
    vendas = []
    bilhetes = []
    capacidade_por_voo = defaultdict(lambda: {'first': 0, 'economy': 0})
    
    for voo in voos:
        assentos_first = [a for a in assentos_por_aviao[voo['no_serie']] if a[1]]
        if assentos_first:
            nif = fake.unique.random_number(digits=9, fix_len=True)
            balcao = random.choice(aeroportos)[0]
            hora_venda = voo['hora_partida'] - timedelta(days=random.randint(1, 30))
            vendas.append((nif, balcao, hora_venda))
            lugar, _ = random.choice(assentos_first)
            preco = round(random.uniform(500, 2000), 2)
            bilhetes.append((len(vendas), voo['no_serie'], voo['hora_partida'], voo['orig'], voo['dest'],
                             fake.name(), preco, True, lugar, voo['no_serie']))
            capacidade_por_voo[(voo['no_serie'], voo['hora_partida'], voo['orig'], voo['dest'])]['first'] += 1
            assentos_por_aviao[voo['no_serie']].remove((lugar, True))
            voo['has_first_class'] = True
        
        assentos_economy = [a for a in assentos_por_aviao[voo['no_serie']] if not a[1]]
        if assentos_economy:
            nif = fake.unique.random_number(digits=9, fix_len=True)
            balcao = random.choice(aeroportos)[0]
            hora_venda = voo['hora_partida'] - timedelta(days=random.randint(1, 30))
            vendas.append((nif, balcao, hora_venda))
            lugar, _ = random.choice(assentos_economy)
            preco = round(random.uniform(50, 500), 2)
            bilhetes.append((len(vendas), voo['no_serie'], voo['hora_partida'], voo['orig'], voo['dest'],
                             fake.name(), preco, False, lugar, voo['no_serie']))
            capacidade_por_voo[(voo['no_serie'], voo['hora_partida'], voo['orig'], voo['dest'])]['economy'] += 1
            assentos_por_aviao[voo['no_serie']].remove((lugar, False))
            voo['has_economy_class'] = True
    
    while len(bilhetes) < TOTAL_BILHETES and len(vendas) < TOTAL_VENDAS:
        available_flights = [v for v in voos if assentos_por_aviao[v['no_serie']]]
        if not available_flights:
            break
        voo = random.choice(available_flights)
        nif = fake.unique.random_number(digits=9, fix_len=True)
        balcao = random.choice(aeroportos)[0]
        hora_venda = voo['hora_partida'] - timedelta(days=random.randint(1, 30))
        vendas.append((nif, balcao, hora_venda))
        num_bilhetes = random.randint(1, min(4, TOTAL_BILHETES - len(bilhetes)))
        for _ in range(num_bilhetes):
            if not assentos_por_aviao[voo['no_serie']]:
                break
            lugar, prim_classe = random.choice(assentos_por_aviao[voo['no_serie']])
            classe = 'first' if prim_classe else 'economy'
            if capacidade_por_voo[(voo['no_serie'], voo['hora_partida'], voo['orig'], voo['dest'])][classe] >= \
               assentos_classe_por_aviao[voo['no_serie']][classe]:
                continue
            preco = round(random.uniform(500, 2000), 2) if prim_classe else round(random.uniform(50, 500), 2)
            bilhetes.append((len(vendas), voo['no_serie'], voo['hora_partida'], voo['orig'], voo['dest'],
                             fake.name(), preco, prim_classe, lugar, voo['no_serie']))
            capacidade_por_voo[(voo['no_serie'], voo['hora_partida'], voo['orig'], voo['dest'])][classe] += 1
            assentos_por_aviao[voo['no_serie']].remove((lugar, prim_classe))
    
    # Ensure every airplane has at least 1 ticket in both classes
    aviao_classe_ticket_check = defaultdict(lambda: {'first': False, 'economy': False})
    voos_por_aviao = defaultdict(list)
    for voo in voos:
        voos_por_aviao[voo['no_serie']].append(voo)
    for _, no_serie, hora_partida, orig, dest, _, _, prim_classe, _, _ in bilhetes:
        classe = 'first' if prim_classe else 'economy'
        aviao_classe_ticket_check[no_serie][classe] = True

    for no_serie, _ in avioes:
        for classe in ['first', 'economy']:
            if not aviao_classe_ticket_check[no_serie][classe]:
                for voo in voos_por_aviao[no_serie]:
                    available = [a for a in assentos_por_aviao[no_serie] if a[1] == (classe == 'first')]
                    if available:
                        lugar, prim_classe = available.pop()
                        assentos_por_aviao[no_serie].remove((lugar, prim_classe))
                        nif = fake.unique.random_number(digits=9, fix_len=True)
                        balcao = random.choice(aeroportos)[0]
                        hora_venda = voo['hora_partida'] - timedelta(days=random.randint(1, 30))
                        vendas.append((nif, balcao, hora_venda))
                        preco = round(random.uniform(500, 2000), 2) if prim_classe else round(random.uniform(50, 500), 2)
                        bilhetes.append((len(vendas), voo['no_serie'], voo['hora_partida'], voo['orig'], voo['dest'],
                                         fake.name(), preco, prim_classe, lugar, no_serie))
                        break

    return vendas, bilhetes

vendas, bilhetes = gerar_vendas_bilhetes()

# SQL output
with open('populate.sql', 'w', encoding='utf-8') as f:
    f.write("-- Aeroportos\n")
    for cod, nome, cidade, pais in aeroportos:
        f.write(f"INSERT INTO aeroporto (codigo, nome, cidade, pais) VALUES ('{cod}', '{nome}', '{cidade}', '{pais}');\n")

    f.write("\n-- Aviões\n")
    for no_serie, modelo in avioes:
        f.write(f"INSERT INTO aviao (no_serie, modelo) VALUES ('{no_serie}', '{modelo}');\n")

    f.write("\n-- Assentos\n")
    for lugar, no_serie, prim_classe in assentos:
        f.write(f"INSERT INTO assento (lugar, no_serie, prim_classe) VALUES ('{lugar}', '{no_serie}', {prim_classe});\n")

    f.write("\n-- Voos\n")
    for voo in voos:
        f.write(f"INSERT INTO voo (no_serie, hora_partida, hora_chegada, partida, chegada) VALUES ("
                f"'{voo['no_serie']}', '{voo['hora_partida']}', '{voo['hora_chegada']}', "
                f"'{voo['orig']}', '{voo['dest']}');\n")

    f.write("\n-- Vendas\n")
    for nif, balcao, hora in vendas:
        f.write(f"INSERT INTO venda (nif_cliente, balcao, hora) VALUES ('{nif}', '{balcao}', '{hora}');\n")

    f.write("\n-- Bilhetes\n")
    for venda_id, no_serie, hora_partida, orig, dest, nome, preco, prim_classe, lugar, no_serie_assento in bilhetes:
        f.write(f"""INSERT INTO bilhete (codigo_reserva, voo_id, nome_passageiro, preco, prim_classe, lugar, no_serie)
    SELECT {venda_id}, v.id, '{nome}', {preco}, {prim_classe}, '{lugar}', '{no_serie_assento}'
    FROM voo v 
    WHERE v.no_serie = '{no_serie}' 
    AND v.hora_partida = '{hora_partida}'
    AND v.partida = '{orig}'
    AND v.chegada = '{dest}';\n""")

print("SQL file generated successfully: populate.sql")