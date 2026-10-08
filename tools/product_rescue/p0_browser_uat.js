// Run with playwright-cli run-code --filename after a fresh page snapshot.
// Uses the real packaged service; browser offline emulation does not stop it.
async page => {
  const evidence = {gate: 'P0_REAL_EXE', started_at: new Date().toISOString()};
  const base = new URL(page.url()).origin;
  const fixture = 'C:/Users/Administrator/Desktop/工作/jiangyi-generator-splitter-audit/docs/v2/integration/fixtures/incident-72cab43961d6488c91b7a9e049265263/';
  const captures = 'C:/xml-uat/product-rescue-p0-20261008/';
  const template = new URL(page.url()).searchParams.get('uat_template') || '1v1';
  evidence.template = template;
  const failures = [];
  page.on('pageerror', error => failures.push(String(error)));
  if (await page.locator('#engineMode').count()) throw new Error('Engine selector still present');
  await page.locator('#newTask').click();
  await page.locator('[data-template="' + template + '"]').click();
  await page.locator('#fileInput').setInputFiles([
    fixture + '九年级上学期物理期末复习（易错精选60题27大考点）（原卷版）.docx',
    fixture + '九年级上学期物理期末复习（易错精选60题27大考点）（解析版）.docx'
  ]);
  await page.getByRole('button', {name: '物理', exact: true}).click();
  await page.locator('#eduLevel').selectOption('初中');
  await page.locator('#gradeSelect').selectOption('九年级');
  const submit = page.waitForResponse(response => response.url() === base + '/api/jobs' && response.request().method() === 'POST');
  await page.locator('#startButton').click();
  const response = await submit;
  if (response.status() !== 202) throw new Error('Submission failed: ' + await response.text());
  const created = await response.json();
  evidence.job_id = created.job_id;
  await page.waitForFunction(id => localStorage.getItem('handout_current_job') === id, created.job_id);
  const beforeRefresh = await (await page.request.get(base + '/api/jobs/' + created.job_id)).json();
  evidence.status_before_refresh = beforeRefresh.status;
  await page.reload();
  await page.waitForFunction(id => localStorage.getItem('handout_current_job') === id && !document.getElementById('progressWrap').hidden, created.job_id);
  evidence.active_job_restored_after_refresh = true;
  await page.context().setOffline(true);
  await page.waitForFunction(() => document.getElementById('connectionLabel').textContent === '连接中断');
  await page.screenshot({path: captures + 'p0-disconnected-' + template + '.png', fullPage: true});
  await page.locator('#reconnect').click();
  await page.waitForFunction(() => document.getElementById('toast').textContent.startsWith('重连失败：'));
  evidence.failed_reconnect_feedback = await page.locator('#toast').innerText();
  // APIRequestContext independently checks that the backend job survives.
  let job;
  const deadline = Date.now() + 120000;
  do {
    const statusResponse = await page.request.get(base + '/api/jobs/' + created.job_id);
    job = await statusResponse.json();
    if (['done', 'partial', 'error'].includes(job.status)) break;
    await new Promise(resolve => setTimeout(resolve, 700));
  } while (Date.now() < deadline);
  if (job.status !== 'done' || job.output_paths.length !== 2) throw new Error('No verified pair: ' + JSON.stringify({status: job.status, error: job.error}));
  evidence.backend_completed_while_disconnected = true;
  await page.context().setOffline(false);
  await page.locator('#reconnect').click();
  await page.waitForFunction(() => document.getElementById('progressTitle').textContent === '讲义已生成');
  evidence.success_reconnect_feedback = await page.locator('#toast').innerText();
  await page.reload();
  await page.waitForFunction(() => document.getElementById('progressTitle').textContent === '讲义已生成');
  evidence.completed_job_restored_after_refresh = await page.evaluate(() => localStorage.getItem('handout_current_job')) === created.job_id;
  const opened = page.waitForResponse(response => response.url().endsWith('/api/open/' + created.job_id));
  await page.locator('#openResult').click();
  evidence.open_result = await (await opened).json();
  const reopened = await page.context().newPage();
  await reopened.goto(base);
  await reopened.waitForFunction(() => document.getElementById('progressTitle').textContent === '讲义已生成');
  evidence.reopened_browser_restores_job = await reopened.evaluate(() => localStorage.getItem('handout_current_job')) === created.job_id;
  await reopened.close();
  await page.screenshot({path: captures + 'p0-completed-restored-' + template + '.png', fullPage: true});
  evidence.job = {status: job.status, generation_attempts: job.generation_attempts, input_version: job.input_version, renderer: job.renderer, output_paths: job.output_paths, package_validation: job.package_validation, warnings: job.warnings};
  evidence.page_errors = failures;
  if (failures.length) throw new Error('Page errors: ' + failures.join('; '));
  return evidence;
}
