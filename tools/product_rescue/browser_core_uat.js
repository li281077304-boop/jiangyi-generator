// Run after a fresh Playwright snapshot. Paths come from the frozen source corpus.
async page => {
  const base = new URL(page.url()).origin;
  const template = new URL(page.url()).searchParams.get('uat_template') || '1v1';
  const root = 'C:/xml-uat/product-rescue-final-20261008/browser-inputs/';
  const cases = [
    {id: 'previously_failed_pair', files: ['物质变化 原卷版.docx', '物质变化 解析版.docx'], status: 'done', count: 2},
    {id: 'teacher_only', files: ['物质变化 解析版.docx'], status: 'done', count: 1},
    {id: 'student_only', files: ['物质变化 原卷版.docx'], status: 'done', count: 1},
    {id: 'zip_partial', files: ['中文批量.zip'], status: 'partial', count: 2}
  ];
  const results = [];
  for (const test of cases) {
    await page.locator('#newTask').click();
    await page.locator('[data-template="' + template + '"]').click();
    await page.locator('#fileInput').setInputFiles(test.files.map(name => root + name));
    await page.getByRole('button', {name: '化学', exact: true}).click();
    await page.locator('#eduLevel').selectOption('初中');
    await page.locator('#gradeSelect').selectOption('九年级');
    const submit = page.waitForResponse(r => r.url() === base + '/api/jobs' && r.request().method() === 'POST');
    await page.locator('#startButton').click();
    const response = await submit;
    if (response.status() !== 202) throw new Error(test.id + ': ' + await response.text());
    const created = await response.json();
    let job;
    const deadline = Date.now() + 120000;
    do {
      job = await (await page.request.get(base + '/api/jobs/' + created.job_id)).json();
      if (['done', 'partial', 'error'].includes(job.status)) break;
      await new Promise(resolve => setTimeout(resolve, 500));
    } while (Date.now() < deadline);
    if (job.status !== test.status || job.output_paths.length !== test.count)
      throw new Error(test.id + ': ' + JSON.stringify(job));
    if (!job.is_batch && job.renderer !== 'XML') throw new Error(test.id + ': expected XML');
    if (job.is_batch && job.items.filter(x => x.status === 'done').some(x => x.renderer !== 'XML'))
      throw new Error(test.id + ': expected XML batch');
    await page.waitForFunction(() => /已生成/.test(document.getElementById('progressTitle').textContent));
    await page.screenshot({path: 'C:/xml-uat/product-rescue-final-20261008/' + test.id + '-' + template + '.png', fullPage: true});
    results.push({case: test.id, template, job});
  }
  return results;
}
