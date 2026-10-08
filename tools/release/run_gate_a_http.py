"""Submit bounded Release Recovery cases to the running Flask HTTP service."""
from __future__ import annotations
import hashlib, json, mimetypes, sys, time, urllib.error, urllib.parse, urllib.request, zipfile
from pathlib import Path

REPO=Path(r"C:\Users\Administrator\Desktop\工作\jiangyi-generator-splitter-audit")
EVIDENCE=Path(r"C:\xml-uat\release-recovery-20261008")
BASE="http://127.0.0.1:5138"
SOURCES=Path(r"C:\xml-uat\stage3-expansion\sources")
CORPUS=json.loads((REPO/"docs/v2/release/PRODUCT_SOURCE_CORPUS.json").read_text(encoding="utf-8"))
EVAL=json.loads((REPO/"docs/v2/integration/fixtures/v12-finalization-evaluation/frozen_evaluation_manifest.json").read_text(encoding="utf-8"))
CORPUS_BY_ID={x["sample_id"]:x for x in CORPUS["samples"]}
EVAL_BY_ID={m["sample_id"]:m for t in EVAL["fixed_topics"] for m in t.get("members",[])}

def digest(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

def frozen_path(sample_id: str):
    if sample_id in CORPUS_BY_ID:
        x=CORPUS_BY_ID[sample_id]; p=Path(x["corpus_path"]); expected=x["sha256"]; name=x["corpus_filename"]
    else:
        x=EVAL_BY_ID[sample_id]; p=Path(x["materialized_path"]); expected=x["sha256"]; name=x["filename"].split("/")[-1]
    actual=digest(p)
    if actual!=expected: raise RuntimeError(f"frozen input changed: {sample_id} {actual} != {expected}")
    return {"sample_id":sample_id,"path":p,"filename":name,"sha256":actual,"bytes":p.stat().st_size}

def build_zip():
    files=[frozen_path(x) for x in ("X005","X006","S04T","S04S")]
    path=EVIDENCE/"chinese_nested_physics_batch.zip"
    with zipfile.ZipFile(path,"w",zipfile.ZIP_DEFLATED) as z:
        for x in files:
            folder="物理/九年级/期末复习" if x["sample_id"] in ("X005","X006") else "物理/九年级/热量与比热容"
            z.write(x["path"],folder+"/"+x["filename"])
        z.writestr("物理/九年级/损坏输入/损坏专题（解析版）.docx",b"PK\\x03\\x04corrupt-docx-fixture")
    return {"path":path,"sha256":digest(path),"bytes":path.stat().st_size,"sources":files,"corrupt_member":"物理/九年级/损坏输入/损坏专题（解析版）.docx"}

def part(boundary: str, headers: list[str], payload: bytes) -> bytes:
    return b"--"+boundary.encode()+b"\r\n"+"\r\n".join(headers).encode("utf-8")+b"\r\n\r\n"+payload+b"\r\n"

def post(fields: dict, files: list[tuple[Path,str]]) -> dict:
    boundary="----CodexGateA"+str(time.time_ns())
    chunks=[]
    for key,value in fields.items():
        chunks.append(part(boundary,[f'Content-Disposition: form-data; name="{key}"'],str(value).encode("utf-8")))
    for path,filename in files:
        fallback="source.docx"
        encoded=urllib.parse.quote(filename.encode("utf-8"))
        disp=f'Content-Disposition: form-data; name="files"; filename="{fallback}"; filename*=UTF-8\'\'{encoded}'
        mime=mimetypes.guess_type(filename)[0] or "application/octet-stream"
        chunks.append(part(boundary,[disp,f"Content-Type: {mime}"],path.read_bytes()))
    chunks.append(b"--"+boundary.encode()+b"--\r\n")
    req=urllib.request.Request(BASE+"/api/jobs",data=b"".join(chunks),headers={"Content-Type":f"multipart/form-data; boundary={boundary}"},method="POST")
    try:
        with urllib.request.urlopen(req,timeout=60) as resp: return {"http_status":resp.status,"body":json.loads(resp.read().decode("utf-8"))}
    except urllib.error.HTTPError as e:
        return {"http_status":e.code,"body":json.loads(e.read().decode("utf-8"))}

def get_job(job_id: str) -> dict:
    with urllib.request.urlopen(BASE+"/api/jobs/"+job_id,timeout=20) as resp: return json.loads(resp.read().decode("utf-8"))

def scenarios():
    x015=frozen_path("X015"); x016=frozen_path("X016"); x008=frozen_path("X008")
    return {
      "x12_4_1v1":{"files":[(x016["path"],x016["filename"]),(x015["path"],x015["filename"])],"sources":[x016,x015],"form":{"subject":"数学","grade":"八年级","handout_type":"专题讲义","academic_year":"2026-2027学年","template_type":"1v1","split_mode":"smart","docx_mode":"auto","engine_mode":"stable_v09"}},
      "x12_4_class":{"files":[(x016["path"],x016["filename"]),(x015["path"],x015["filename"])],"sources":[x016,x015],"form":{"subject":"数学","grade":"八年级","handout_type":"专题讲义","academic_year":"2026-2027学年","template_type":"class","split_mode":"smart","docx_mode":"auto","engine_mode":"stable_v09"}},
      "x008_teacher_only":{"files":[(x008["path"],x008["filename"])],"sources":[x008],"form":{"subject":"物理","grade":"九年级","handout_type":"同步讲义","academic_year":"2026-2027学年","template_type":"1v1","split_mode":"smart","docx_mode":"auto","engine_mode":"stable_v09"}},
      "x015_student_only":{"files":[(x015["path"],x015["filename"])],"sources":[x015],"form":{"subject":"数学","grade":"八年级","handout_type":"专题讲义","academic_year":"2026-2027学年","template_type":"1v1","split_mode":"smart","docx_mode":"auto","engine_mode":"stable_v09"}},
    }

def run(name: str, spec: dict) -> dict:
    created=post(spec["form"],spec["files"])
    record={"scenario":name,"submitted_at":time.time(),"form":spec["form"],"sources":[{k:v for k,v in x.items() if k!="path"}|{"path":str(x["path"])} for x in spec["sources"]],"submission":created}
    folder=EVIDENCE/"http_matrix"/name; folder.mkdir(parents=True,exist_ok=True)
    # ZIP evidence includes nested source records; normalize pathlib paths in
    # those records without changing the submitted bytes or source lineage.
    (folder/"created.json").write_text(json.dumps(record,ensure_ascii=False,indent=2,default=str)+"\n",encoding="utf-8")
    job_id=created.get("body",{}).get("job_id")
    if not job_id: return record
    deadline=time.time()+600; last=None
    while time.time()<deadline:
        j=get_job(job_id); status=j.get("status")
        if status!=last:
            print(f"{name} {job_id} {status} {j.get('stage')}",flush=True); last=status
            (folder/"latest.json").write_text(json.dumps(j,ensure_ascii=False,indent=2,default=str)+"\n",encoding="utf-8")
        if status in ("done","partial","error","failed"): break
        time.sleep(2)
    else: j={"job_id":job_id,"status":"timeout"}
    record["job_id"]=job_id; record["job"]=j
    (folder/"terminal.json").write_text(json.dumps(record,ensure_ascii=False,indent=2,default=str)+"\n",encoding="utf-8")
    return record

if __name__=="__main__":
    names=sys.argv[1:]
    spec=scenarios()
    if "s04_batch" in names:
        z=build_zip(); spec["s04_batch"]={"files":[(z["path"],"九年级物理_两专题加损坏项.zip")],"sources":[{k:v for k,v in z.items() if k!="path"}|{"path":str(z["path"])}],"form":{"subject":"物理","grade":"九年级","handout_type":"同步讲义","academic_year":"2026-2027学年","template_type":"class","split_mode":"smart","docx_mode":"auto","engine_mode":"stable_v09"}}
    if not names: raise SystemExit("pass scenario ids: x12_4_1v1 x12_4_class x008_teacher_only x015_student_only s04_batch")
    for name in names:
        if name not in spec: raise SystemExit("unknown scenario: "+name)
        r=run(name,spec[name]); print(json.dumps({"scenario":name,"job_id":r.get("job_id"),"status":r.get("job",{}).get("status"),"renderer":r.get("job",{}).get("renderer_route"),"elapsed":r.get("job",{}).get("elapsed_seconds")},ensure_ascii=False),flush=True)
