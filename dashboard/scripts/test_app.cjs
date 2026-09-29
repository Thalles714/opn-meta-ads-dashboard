const assert=require('node:assert/strict');
const {existsSync}=require('node:fs');
const {join}=require('node:path');
const local=join(__dirname,'../public/app.js');
const {total,ratio,filterRows,groupRows}=require(existsSync(local)?local:join(__dirname,'../../app.js'));
const rows=[
  {d:'2026-09-01',c:'C1',s:'S1',a:'A1',t:'conversation',spend:10000,impressions:1000,link_clicks:100,conversations:10,profile_visits:null,purchases:null},
  {d:'2026-09-02',c:'C1',s:'S1',a:'A1',t:'conversation',spend:100,impressions:100,link_clicks:1,conversations:0,profile_visits:null,purchases:null},
  {d:'2026-09-02',c:'C2',s:'S2',a:'A2',t:'visit',spend:300,impressions:0,link_clicks:null,conversations:null,profile_visits:5,purchases:null},
];
assert.equal(total(rows,'spend'),10400);
assert.equal(total(rows,'profile_visits'),5);
assert.equal(total(rows,'purchases'),null);
assert.equal(ratio(100,0),null);
assert.equal(ratio(100,null),null);
assert.equal(ratio(total(rows,'spend'),total(rows,'link_clicks')),10400/101);
assert.notEqual(ratio(total(rows,'spend'),total(rows,'link_clicks')),(10000/100+100/1)/2);
assert.equal(filterRows(rows,{from:'2026-09-02',to:'2026-09-02'}).length,2);
assert.equal(filterRows(rows,{from:'2026-09-02',to:'2026-09-02',c:'C1',s:'S1',a:'A1',t:'conversation'}).length,1);
assert.equal(filterRows(rows,{from:'2026-09-03',to:'2026-09-03'}).length,0);
assert.equal(groupRows(rows,'campaign').length,2);
assert.equal(groupRows(rows,'campaign').find(x=>x.label==='C1').conversations,10);
assert.equal(groupRows(rows,'campaign').find(x=>x.label==='C2').conversations,null);
assert.ok(rows.every(r=>!('reach' in r)));
console.log('test_app: OK');
