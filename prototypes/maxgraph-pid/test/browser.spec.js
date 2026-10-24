import {test,expect} from '@playwright/test';
test('real maxGraph displays P&ID and engineering edit',async({page})=>{
  await page.goto('/');
  await expect(page.locator('#engine')).toContainText('maxGraph');
  await expect(page.locator('#status')).toContainText('11 objects · 19 directed connections');
  await expect(page.locator('#graph svg')).toBeVisible();
  await page.getByRole('button',{name:'2 · PFD'}).click();
  await expect(page.locator('#view-label')).toContainText('PFD');
  await page.getByRole('button',{name:'3 · P&ID'}).click();
  await page.getByRole('button',{name:'Insert discharge valve'}).click();
  await expect(page.locator('#status')).toContainText('12 objects · 21 directed connections');
  await expect(page.locator('#activity')).toContainText('XV-102 inserted');
  await expect(page.locator('#properties')).toContainText('valve-dis-1');
  const count=await page.evaluate(()=>window.__pidDemo.model().edges.length);
  expect(count).toBe(21);
});
