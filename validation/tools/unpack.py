"""Проверка SHA256 и безопасная распаковка неизменных проверочных зависимостей."""
import hashlib,json,sys,tarfile
from pathlib import Path
here,work=map(Path,sys.argv[1:]);(work/'results').mkdir()
expected={'lidar-near-direct-v4-validation.tar.gz':'7cafe36d8be69addc682ada305d4fb5661885b00d14bf3c6d21c36cb472f7a75','lidar-near-direct-v4.tar.gz':'e8a207a8e5f588e344a9ae06e90e6be8658865fa10a5ca582a7978945d6b80f1','lidar-near-query-first-validation.tar.gz':'cb807a19518edc00d3e2ffaf2799b9ec9b7c981d3d60947d470bad2bc29b6c6e','lidar-near-query-first.tar.gz':'e66b093a46bb595d84bd2f1e09afc4c1c991d6585ff193154cf0b01bf80d407e'}
for name,digest in expected.items():
 p=here/'archives'/name
 with p.open('rb') as f:
  h=hashlib.sha256()
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 assert h.hexdigest()==digest,name
 target=work if '-validation.' in name else work/'direct-validation'
 with tarfile.open(p) as tar:
  members=tar.getmembers()
  for m in members:
   q=Path(m.name);assert not q.is_absolute() and '..' not in q.parts and (m.isfile() or m.isdir()),m.name
   if m.isfile():assert not (target/q).exists(),m.name
  tar.extractall(target,members=members)
(work/'results/archive_integrity.json').write_text(json.dumps({'status':'PASS','archives':expected},indent=2))
print('SHA256 и безопасная распаковка: PASS',flush=True)
