// Run against the extracted normal EXE after a current Playwright snapshot.
async page => {
  const base = new URL(page.url()).origin;
  await page.locator('#newTask').click();
  await page.locator('[data-template="1v1"]').click();
  await page.locator('#fileInput').setInputFiles([
    'C:/xml-uat/product-rescue-final-20261008/browser-inputs/氧气 原卷版.docx',
    'C:/xml-uat/product-rescue-final-20261008/browser-inputs/氧气 解析版.docx'
  ]);
  await page.getByRole('button', {name: '化学', exact: true}).click();
  await page.locator('#eduLevel').selectOption('初中');
  await page.locator('#gradeSelect').selectOption('九年级');
  const submitted = page.waitForResponse(r => r.url() === base + '/api/jobs' && r.request().method() === 'POST');
  await page.locator('#startButton').click();
  const response = await submitted;
  if (response.status() !== 202) throw new Error(await response.text());
  const created = await response.json();
  let job;
  const deadline = Date.now() + 120000;
  do {
    job = await (await page.request.get(base + '/api/jobs/' + created.job_id)).json();
    if (['done', 'error', 'partial'].includes(job.status)) break;
    await new Promise(resolve => setTimeout(resolve, 500));
  } while (Date.now() < deadline);
  if (job.status !== 'error' || job.has_result || job.output_paths.length)
    throw new Error('Unsafe success or publication: ' + JSON.stringify(job));
  if (!job.error.includes('PRODUCT_TEXTBOX_CONTENT_UNPROVEN') || !job.error.includes('原文文本框'))
    throw new Error('Missing clear content failure reason: ' + job.error);
  await page.waitForFunction(() => document.body.innerText.includes('原文文本框中的部分正文未能完整保留'));
  await page.screenshot({path: 'C:/xml-uat/product-rescue-safe-20261008/content-refused.png', fullPage: true});
  await page.reload();
  await page.waitForFunction(() => document.body.innerText.includes('原文文本框中的部分正文未能完整保留'));
  return {gate: 'EXE_CONTENT_REFUSAL', job_id: job.job_id, status: job.status,
    renderer: job.renderer, fallback_reason: job.fallback_reason, error: job.error,
    output_paths: job.output_paths, has_result: job.has_result,
    product_integrity: job.product_integrity, refusal_persisted_after_refresh: true};
}
