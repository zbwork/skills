"""Validate editable resources and build an atomic Pages/Release publication."""
import argparse, hashlib, io, json, pathlib, re, shutil, zipfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
def sha(body):return hashlib.sha256(body).hexdigest()
def dump(path,data):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
def zip_bytes(files):
    output=io.BytesIO()
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,body,mode in files:
            i=zipfile.ZipInfo(name,(2020,1,1,0,0,0));i.compress_type=zipfile.ZIP_DEFLATED;i.external_attr=(0o100000|mode)<<16;z.writestr(i,body)
    return output.getvalue()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--check',action='store_true');ap.add_argument('--local',action='store_true');args=ap.parse_args()
    config=json.loads((ROOT/'resource.json').read_text());repo=config['repository'];release=config['release']
    if not re.fullmatch(r'[\w.-]+/[\w.-]+',repo) or not re.fullmatch(r'[\w.-]+',release):raise ValueError('Invalid repository/release')
    stage=ROOT/'_site.next';shutil.rmtree(stage,ignore_errors=True);stage.mkdir()
    (stage/'packages').mkdir();shutil.copytree(ROOT/'assets',stage/'assets')
    catalogs={name:json.loads((ROOT/'catalog/v1'/f'{name}.json').read_text()) for name in ['skills']}
    skills=catalogs['skills']['data']['items']
    def unique(rows,key):
        values=[r[key] for r in rows]
        if len(set(values))!=len(values):raise ValueError('Duplicate '+key)
        return set(values)
    skill_ids=unique(skills,'skill_uuid');unique(skills,'code')
    forbidden=re.compile(rb'(?<![A-Za-z0-9_])(?:sk-[A-Za-z0-9_-]{30,}|gh[pousr]_[A-Za-z0-9]{30,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|AKIA[A-Z0-9]{16})')
    for item in skills:
        code=item['code'];version=item['latest_version']
        if not re.fullmatch(r'[A-Za-z0-9_-]+',code):raise ValueError('Unsafe skill code')
        folder=ROOT/'skills'/code;files=[];seen=set()
        for path in sorted(folder.rglob('*')):
            if path.is_symlink():raise ValueError('Symlink not allowed: '+str(path))
            if not path.is_file():continue
            name=path.relative_to(folder).as_posix()
            if any(p in ('','.','..') for p in name.split('/')) or '\\' in name or name.lower() in seen:raise ValueError('Unsafe/duplicate path')
            seen.add(name.lower());body=path.read_bytes()
            if forbidden.search(body):raise ValueError('Credential-like content in '+code+'/'+name)
            files.append((name,body,0o755 if path.stat().st_mode&0o111 else 0o644))
        if 'skill.md' not in seen or len(files)>2000 or sum(len(b) for _,b,_ in files)>100*1024*1024:raise ValueError('Invalid skill source: '+code)
        inner=zip_bytes(files)
        if len(inner)>50*1024*1024:raise ValueError('Skill package too large')
        manifest={'format_version':1,'skills':[{'code':code,'version':{'version':version,'package_path':'skill.zip','package_sha256':sha(inner)}}]}
        outer=zip_bytes([('manifest.json',json.dumps(manifest).encode(),0o644),('skill.zip',inner,0o644)])
        digest=sha(outer);filename=f'{code}-{digest}.zip';(stage/'packages'/filename).write_bytes(outer)
        item['bundle_sha256']=digest;item['bundle_url']=('packages/'+filename if args.local else f'https://github.com/{repo}/releases/download/{release}/{filename}')
    for rows,field in [(skills,'icon_url')]:
        for item in rows:
            value=item.get(field,'')
            if not value:continue
            path=pathlib.PurePosixPath(value)
            if path.is_absolute() or '..' in path.parts or not value.startswith('assets/'):raise ValueError('Non-local image')
            body=(stage/path).read_bytes()
            if sha(body)!=path.stem:raise ValueError('Image digest mismatch')
    for name,data in catalogs.items():
        data['data']['total']=len(data['data']['items']);dump(stage/'catalog/v1'/f'{name}.json',data)
    (stage/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>知办AI 官方资源</title><h1>知办AI 官方资源</h1><p>数字员工、技能目录、图标与版本化技能包。</p>')
    (stage/'.nojekyll').touch()
    if args.check:shutil.rmtree(stage)
    else:
        shutil.rmtree(ROOT/'_site',ignore_errors=True);stage.rename(ROOT/'_site')
    print(f'Validated {len(skills)} skills; {len(list((ROOT/"assets").rglob("*.*")))} images')
if __name__=='__main__':main()
