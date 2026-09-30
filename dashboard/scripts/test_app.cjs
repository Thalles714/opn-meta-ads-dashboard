const assert=require('node:assert/strict');
const {existsSync}=require('node:fs');
const {join}=require('node:path');
const local=join(__dirname,'../public/app.js');
const {total,ratio,filterRows,groupRows,hasActivity,metricTotal,buildSeries,weekStart,exportComparison}=require(existsSync(local)?local:join(__dirname,'../../app.js'));
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
assert.equal(filterRows(rows,{from:'2026-09-02',to:'2026-09-02',t:'conversation'}).length,2);
assert.equal(filterRows(rows,{from:'2026-09-02',to:'2026-09-02',c:'C1',s:'S1',a:'A1',t:'conversation'}).length,1);
assert.equal(filterRows(rows,{from:'2026-09-03',to:'2026-09-03'}).length,0);
assert.equal(groupRows(rows,'campaign').length,2);
assert.equal(groupRows(rows,'campaign').find(x=>x.label==='C1').conversations,10);
assert.equal(groupRows(rows,'campaign').find(x=>x.label==='C2').conversations,null);
assert.ok(rows.every(r=>!('reach' in r)));
assert.equal(metricTotal(rows,'ctr'),101/1100*100);
assert.equal(metricTotal(rows,'cpc'),10400/101);
assert.equal(metricTotal(rows,'cpm'),10400/1100*1000);
const purchaseRows=[{...rows[0],purchases:2,purchase_value:12345},{...rows[1],purchases:0,purchase_value:0}];
assert.equal(metricTotal(purchaseRows,'purchase_value'),12345);
assert.equal(groupRows(purchaseRows,'campaign')[0].purchase_value,12345);
assert.ok(exportComparison(purchaseRows,'campaign','2026-09-01','2026-09-02').includes('"123,45"'));
assert.ok(exportComparison([{...rows[0],c:'=1+1'}],'campaign','2026-09-01','2026-09-01').includes('"\'=1+1"'));
assert.equal(weekStart('2026-09-02'),'2026-08-31');
assert.deepEqual(buildSeries(rows,'spend','day','2026-09-01','2026-09-03').map(x=>x.value),[10000,400,null]);
assert.deepEqual(buildSeries(rows,'spend','week','2026-09-01','2026-09-03').map(x=>x.value),[10400]);
assert.deepEqual(buildSeries(rows,'spend','month','2026-09-01','2026-09-03').map(x=>x.value),[10400]);
assert.equal(buildSeries(rows,'profile_visits','day','2026-09-01','2026-09-02')[0].value,null);
assert.equal(buildSeries(rows,'profile_visits','day','2026-09-01','2026-09-02')[1].value,5);
assert.equal(hasActivity({spend:0,impressions:0,link_clicks:null,landing_page_views:null,conversations:null,profile_visits:null,purchases:0}),false);
assert.equal(hasActivity({spend:100,impressions:0,link_clicks:null,landing_page_views:null,conversations:null,profile_visits:null,purchases:0}),true);
console.log('test_app: OK');
