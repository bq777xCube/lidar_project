"""Проверка точности локализации исходного пакета без изменения эталонов."""
import ast,hashlib,json,re,sys,xml.etree.ElementTree as ET
from pathlib import Path
old,new=map(Path,sys.argv[1:3]);dest=Path(sys.argv[3]);records=[]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
class Strip(ast.NodeTransformer):
 def __init__(self,metadata=False):self.metadata=metadata
 def visit(self,n):
  if isinstance(n,(ast.Module,ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef)) and n.body and isinstance(n.body[0],ast.Expr) and isinstance(n.body[0].value,ast.Constant) and isinstance(n.body[0].value.value,str):n.body=n.body[1:]
  if self.metadata and isinstance(n,ast.keyword) and n.arg=='description':n.value=ast.Constant(value='METADATA_DESCRIPTION')
  return super().visit(n)
for name in json.loads((old/'runtime_manifest.json').read_text())['archive_allowlist']:
 if name in ['README.md','runtime_manifest.json']:continue
 a,b=old/name,new/name;aa,bb=a.read_text(),b.read_text();kind='byte_exact'
 if a.suffix=='.py':
  assert '__doc__' not in aa and 'doctest' not in aa
  assert ast.dump(Strip(name.endswith('setup.py')).visit(ast.parse(aa)))==ast.dump(Strip(name.endswith('setup.py')).visit(ast.parse(bb))),name;kind='AST_equal_without_true_docstrings_and_setup_description'
 elif a.suffix=='.cpp':
  tokens=lambda s:re.findall(r'"(?:\\.|[^"\\])*"|\w+|[^\s]',re.sub(r'//[^\n]*','',s))
  assert tokens(aa)==tokens(bb),name;kind='CPP_significant_tokens_equal'
 elif name=='Dockerfile' or a.suffix=='.sh':
  strip=lambda s:'\n'.join(l for l in s.splitlines() if not l.lstrip().startswith('#') or l.startswith('#!'))
  assert strip(aa)==strip(bb),name;kind='instructions_equal'
 elif name.endswith('package.xml'):
  x,y=ET.fromstring(aa),ET.fromstring(bb);x.find('description').text='DESCRIPTION';y.find('description').text='DESCRIPTION';assert ET.tostring(x)==ET.tostring(y);kind='XML_equal_except_description'
 else:assert a.read_bytes()==b.read_bytes(),name
 records.append(dict(file=name,change='перевод пояснений' if aa!=bb else 'без изменений',check=kind,original_sha256=sha(a),ru_sha256=sha(b)))
result={'status':'PASS','files':records,'docstrings_not_used_by_runtime':True,'allowed_help_strings':['setup.py:setup(description=...)','package.xml:description'], 'exceptions':['Идентификаторы, ключи, reason/status-коды, строки результатов, исключений и логов сохранены как контракты.','maintainer/example.invalid: исторические метаданные, не подтвержденные контакты команды.','Лицензия Proprietary и уведомления upstream не меняются.','Исторические проверки и эталоны поставляются без перевода как неизменные проверочные данные.'],'native_flags':['-std=c++17','-O3','-fno-fast-math','-ffp-contract=off','-shared','-fPIC']}
dest.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print('PASS: семантика локализации,',len(records),'файла')
