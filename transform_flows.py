"""
transform_flows.py
==================
Script untuk mengkonversi flows.json dari arsitektur main.py
ke arsitektur server_vps.py (MySQL polling).

Jalankan di VPS:
  python3 ~/transform_flows.py
"""
import json, copy, os

FLOWS_PATH = os.path.expanduser('~/.node-red/flows.json')
BACKUP_PATH = FLOWS_PATH + '.bak'
TAB_ID = '11085f20bdad7e65'
MYSQL_CFG = '9e01eb60cace409c'

with open(FLOWS_PATH) as f:
    flows = json.load(f)
with open(BACKUP_PATH, 'w') as f:
    json.dump(flows, f)
print(f'Backup: {BACKUP_PATH}')

nodes = {n['id']: n for n in flows if isinstance(n, dict) and 'id' in n}

# 1. DISABLE TCP & INSERT nodes (tidak dipakai di VPS)
for nid in [
    '5e51653c36446d2b',  # TCP in 5020
    'ead7eefc72f76adf',  # JSON parse dari TCP
    '98b91cfccfca7c70',  # TCP out 5021
    '2d81ebc87833e4b8',  # Filter Rekomendasi dari TCP
    '39880dfe386d58b1', 'a2c081b1b81e7f92', '07323820c541af03',  # INSERT slave_1
    'a1572e686b56b795', 'a958606504874033', '9324464cdc9dfd45',  # INSERT slave_2
    '5917fd533d5ab578', 'ee55641c5f80cb5b', 'd76615c078914e3d',  # INSERT slave_3
]:
    if nid in nodes:
        nodes[nid]['d'] = True

# 2. ENABLE semua node Slave 1 & 3 yang disabled
for nid in [
    '2cbb60bc2726c32a','1bed901fb4462865','9ce7b8abd4f17139','243488c73283c4d2',
    'e157ef409d90bd53','d402279ead095f85','0b0710dc98283e23','352d4186435110b5',
    '21bbd0af137bccb6','31a35b21de999205','c1a433ffd57a94f0','af7eab6e5452a285',
    '38350e90fb50393e','08308a9eab1abc4c','2684c7f28b905fdf',
    'b369070f42a7e855','fe9f015d5eebc4e5','241e7e1e4ab76734','c9fbdcc2813b251e',
    '5dc84ffa14d58256','89dc43db9bdf0e98','96941cbffb193240',
    '77aa4c9a4a287234','8b992c2a65916033','4122327bc0f276f2','3cf4f8ef9b44e699',
    'e61310fa352cf0d0','7e4c827732b3f863','018c93cba6561905','e055a9de0f078429',
    '7a2f1e2c38f2ae6f','afd6ed5288f3565f','8eb790a7872937f6','f50b0d9636137144',
    '6ee9edb07fdff2fe','d767044530b0b92d','a194ebf765352a6f',
    'ce51ab6677330261','e00dc8e827741577','558f2f865103e681','8c0327f961fa3a1e',
    'ce8c9632804345fa','dd06e3c073ff1162','e5ae928b23086e21',
]:
    if nid in nodes:
        nodes[nid].pop('d', None)

# 3. FIX nama field di extractor functions (data.kelembapan_tanah → kelembapan)
FIELD_FIXES = {
    '1bed901fb4462865': "msg.payload = msg.payload.kelembapan;\nreturn msg;",
    '9ce7b8abd4f17139': "msg.payload = msg.payload.suhu;\nreturn msg;",
    '243488c73283c4d2': "msg.payload = msg.payload.ph;\nreturn msg;",
    'e157ef409d90bd53': "msg.payload = msg.payload.nitrogen;\nreturn msg;",
    'd402279ead095f85': "msg.payload = msg.payload.fosfor;\nreturn msg;",
    '0b0710dc98283e23': "msg.payload = msg.payload.kalium;\nreturn msg;",
    '352d4186435110b5': "msg.payload = msg.payload.salinity;\nreturn msg;",
    '6385c85c4e7739e7': "msg.payload = msg.payload.kelembapan;\nreturn msg;",
    'd3c670fe854a563f': "msg.payload = msg.payload.suhu;\nreturn msg;",
    '7eac71318b323c8f': "msg.payload = msg.payload.ph;\nreturn msg;",
    '6254f242fa60855a': "msg.payload = msg.payload.nitrogen;\nreturn msg;",
    'e65f9717871aa774': "msg.payload = msg.payload.fosfor;\nreturn msg;",
    'f4023589d9abf493': "msg.payload = msg.payload.kalium;\nreturn msg;",
    '44ab622b30ea15e9': "msg.payload = msg.payload.salinity;\nreturn msg;",
    '8b992c2a65916033': "msg.payload = msg.payload.kelembapan;\nreturn msg;",
    '4122327bc0f276f2': "msg.payload = msg.payload.suhu;\nreturn msg;",
    '3cf4f8ef9b44e699': "msg.payload = msg.payload.ph;\nreturn msg;",
    'e61310fa352cf0d0': "msg.payload = msg.payload.nitrogen;\nreturn msg;",
    '7e4c827732b3f863': "msg.payload = msg.payload.fosfor;\nreturn msg;",
    '018c93cba6561905': "msg.payload = msg.payload.kalium;\nreturn msg;",
    'e055a9de0f078429': "msg.payload = msg.payload.salinity;\nreturn msg;",
}
for nid, func in FIELD_FIXES.items():
    if nid in nodes:
        nodes[nid]['func'] = func

# 4. FIX slave filter: tidak perlu cek slave_id, langsung unpack array dari MySQL
SLAVE_PASS = "if (!msg.payload || msg.payload.length === 0) return null;\nmsg.payload = msg.payload[0];\nreturn msg;"
for nid in ['2cbb60bc2726c32a', 'e39abcfb4c204285', '77aa4c9a4a287234']:
    if nid in nodes:
        nodes[nid]['func'] = SLAVE_PASS

# 5. Rewire tombol Generate → query rekomendasi (bukan TCP out)
REKOM_SET_QUERY_ID = 'vps_rekom_set_query'
REKOM_MYSQL_ID     = 'vps_rekom_mysql'
REKOM_TRANSFORM_ID = 'vps_rekom_transform'
REKOM_TEMPLATE_ID  = 'f6359da806e01927'  # template yang sudah ada

if '8b47a4d00813eaac' in nodes:
    nodes['8b47a4d00813eaac']['wires'] = [[REKOM_SET_QUERY_ID]]

# 6. TAMBAH NODE BARU ke flows
new_nodes = [
    # --- MySQL polling Slave 1 ---
    {"id":"vps_inject_s1","type":"inject","z":TAB_ID,"name":"Poll Slave 1 (5s)",
     "repeat":"5","once":True,"onceDelay":0.5,"topic":"","payload":"","payloadType":"date",
     "wires":[["vps_query_s1"]]},
    {"id":"vps_query_s1","type":"function","z":TAB_ID,"name":"Query slave_1",
     "func":"msg.topic = 'SELECT kelembapan,suhu,ph,nitrogen,fosfor,kalium,salinity FROM slave_1 ORDER BY timestamp DESC LIMIT 1';\nreturn msg;",
     "outputs":1,"wires":[["vps_mysql_s1"]]},
    {"id":"vps_mysql_s1","type":"mysql","z":TAB_ID,"name":"MySQL slave_1",
     "mydb":MYSQL_CFG,"wires":[["2cbb60bc2726c32a"]]},

    # --- MySQL polling Slave 2 ---
    {"id":"vps_inject_s2","type":"inject","z":TAB_ID,"name":"Poll Slave 2 (5s)",
     "repeat":"5","once":True,"onceDelay":1.5,"topic":"","payload":"","payloadType":"date",
     "wires":[["vps_query_s2"]]},
    {"id":"vps_query_s2","type":"function","z":TAB_ID,"name":"Query slave_2",
     "func":"msg.topic = 'SELECT kelembapan,suhu,ph,nitrogen,fosfor,kalium,salinity FROM slave_2 ORDER BY timestamp DESC LIMIT 1';\nreturn msg;",
     "outputs":1,"wires":[["vps_mysql_s2"]]},
    {"id":"vps_mysql_s2","type":"mysql","z":TAB_ID,"name":"MySQL slave_2",
     "mydb":MYSQL_CFG,"wires":[["e39abcfb4c204285"]]},

    # --- MySQL polling Slave 3 ---
    {"id":"vps_inject_s3","type":"inject","z":TAB_ID,"name":"Poll Slave 3 (5s)",
     "repeat":"5","once":True,"onceDelay":2.5,"topic":"","payload":"","payloadType":"date",
     "wires":[["vps_query_s3"]]},
    {"id":"vps_query_s3","type":"function","z":TAB_ID,"name":"Query slave_3",
     "func":"msg.topic = 'SELECT kelembapan,suhu,ph,nitrogen,fosfor,kalium,salinity FROM slave_3 ORDER BY timestamp DESC LIMIT 1';\nreturn msg;",
     "outputs":1,"wires":[["vps_mysql_s3"]]},
    {"id":"vps_mysql_s3","type":"mysql","z":TAB_ID,"name":"MySQL slave_3",
     "mydb":MYSQL_CFG,"wires":[["77aa4c9a4a287234"]]},

    # --- Rekomendasi dari MySQL (tombol Generate) ---
    {"id":REKOM_SET_QUERY_ID,"type":"function","z":TAB_ID,"name":"Query Rekomendasi",
     "func":"msg.topic = 'SELECT * FROM rekomendasi ORDER BY timestamp DESC LIMIT 1';\nreturn msg;",
     "outputs":1,"wires":[[REKOM_MYSQL_ID]]},
    {"id":REKOM_MYSQL_ID,"type":"mysql","z":TAB_ID,"name":"MySQL rekomendasi",
     "mydb":MYSQL_CFG,"wires":[[REKOM_TRANSFORM_ID]]},
    {"id":REKOM_TRANSFORM_ID,"type":"function","z":TAB_ID,"name":"Transform Rekomendasi",
     "func":(
        "if (!msg.payload || msg.payload.length === 0) { msg.payload = []; return msg; }\n"
        "var r = msg.payload[0];\n"
        "var hasil = [];\n"
        "for (var i = 1; i <= 5; i++) {\n"
        "    var nama = r['tanaman_' + i];\n"
        "    var skor = r['skor_' + i];\n"
        "    if (nama && skor !== null) {\n"
        "        var status = skor >= 80 ? 'Sangat Cocok' : skor >= 60 ? 'Cocok' : skor >= 40 ? 'Cukup Cocok' : 'Kurang Cocok';\n"
        "        hasil.push({ nama: nama, skor: parseFloat(skor.toFixed(1)), status: status });\n"
        "    }\n"
        "}\n"
        "msg.payload = hasil;\n"
        "return msg;"
     ),
     "outputs":1,"wires":[[REKOM_TEMPLATE_ID]]},
]

flows.extend(new_nodes)

with open(FLOWS_PATH, 'w') as f:
    json.dump(flows, f, ensure_ascii=False)

print(f'\nSelesai! {len(new_nodes)} node baru ditambahkan.')
print('Restart Node-RED: sudo systemctl restart node-red')
