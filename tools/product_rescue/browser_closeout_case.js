// Runner replaces __CONFIG__ with a verified immutable-source case.
async page => {
  const cfg = __CONFIG__;
  const base = new URL(page.url()).origin;
  await page.locator('#newTask').click();
  await page.locator('[data-template="'+cfg.template+'"]').click();
  await page.locator('#fileInput').setInputFiles(cfg.files);
  await page.getByRole('button',{name:cfg.subject,exact:true}).click();
  await page.locator('#eduLevel').selectOption('初中');
  await page.locator('#gradeSelect').selectOption(cfg.grade);
  const submit=page.waitForResponse(r=>r.url()===base+'/api/jobs' && r.request().method()==='POST');
  await page.locator('#startButton').click();
  const response=await submit, created=await response.json();
  if(response.status()!==202) {
    if(cfg.expectedErrorText) await page.waitForFunction(text=>document.body.innerText.includes(text),cfg.expectedErrorText);
    if(cfg.screenshot) await page.screenshot({path:cfg.screenshot,fullPage:true});
    return {case:cfg.id,template:cfg.template,http_status:response.status(),status:'rejected',error:created,source_hashes:cfg.source_hashes};
  }
  let job; const deadline=Date.now()+600000;
  do {
    job=await (await page.request.get(base+'/api/jobs/'+created.job_id)).json();
    if(!cfg.wait || ['done','error','partial'].includes(job.status)) break;
    await new Promise(resolve=>setTimeout(resolve,700));
  } while(Date.now()<deadline);
  if(cfg.screenshot) await page.screenshot({path:cfg.screenshot,fullPage:true});
  return {case:cfg.id,template:cfg.template,http_status:202,source_hashes:cfg.source_hashes,job};
}
