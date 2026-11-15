/* Read the publicly rendered origin with normal Chromium, then use IndexNow's
   documented JSON API. No proxy, fingerprint change or authentication bypass. */
const {chromium}=require('playwright');
const fs=require('fs');
const origin='https://sho-monoyori-review.zodiac-suu.workers.dev';
(async()=>{
  const browser=await chromium.launch();
  try{
    const page=await browser.newPage();
    const read=async path=>{const r=await page.goto(origin+path);if(!r||r.status()!==200)throw Error('Public discovery resource unavailable: '+path);return r.text();};
    if((await read('/robots.txt')).includes('Disallow: /'))throw Error('Crawling blocked');
    const key=JSON.parse(fs.readFileSync('portal-tools/indexnow_config.json','utf8')).key;
    if((await read('/'+key+'.txt')).trim()!==key)throw Error('Ownership verification file mismatch');
    const xml=await read('/sitemap.xml');
    const urls=[...xml.matchAll(/<loc>([^<]+)<\/loc>/g)].map(x=>x[1]);
    if(!urls.length||urls.some(x=>!x.startsWith(origin+'/')))throw Error('Unexpected sitemap origin');
    const response=await fetch('https://api.indexnow.org/indexnow',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({host:new URL(origin).hostname,key,keyLocation:origin+'/'+key+'.txt',urlList:urls})});
    if(![200,202].includes(response.status))throw Error('IndexNow response '+response.status);
    const receipt={origin,submitted_urls:urls.length,http_status:response.status,indexed_urls:null,note:'Submission only. Search inclusion and traffic are not confirmed.'};
    fs.mkdirSync('review-proof',{recursive:true});fs.writeFileSync('review-proof/search-submission.json',JSON.stringify(receipt,null,2));console.log(JSON.stringify(receipt));
  }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
