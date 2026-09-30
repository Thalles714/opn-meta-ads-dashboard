import unittest
from datetime import date
from pipeline import parse, number, sums, digest, merge_records, public_data

def row(day='2026-09-01', ad='3', spend='1,23', conversations='1'):
    return {'Início dos relatórios':day,'Encerramento dos relatórios':day,'Nome da campanha':'Campanha','Nome do conjunto de anúncios':'Conjunto','Nome do anúncio':'Anúncio',
            'Identificação da campanha':'1','Identificação do conjunto de anúncios':'2','Identificação do anúncio':ad,
            'Indicador de resultados':'actions:onsite_conversion.messaging_conversation_started_7d','Resultados':conversations,
            'Configuração de atribuição':'Clique de 7 dias ou visualização de 1 dia',
            'Valor gasto (BRL)':spend,'Impressões':'100','Cliques no link':'5','Visualizações da página de destino':'',
            'Conversas por mensagem iniciadas':conversations,'Visitas ao perfil do Instagram':'','Compras':'',
            'Valor de conversão da compra':'','site - lead (clicou motor reserva)':'','site - lead (clicou whats)':''}

class PipelineTest(unittest.TestCase):
    def parse(self,rows):return parse(rows,date(2026,9,1),date(2026,9,30))
    def test_locale_and_missing(self):
        records,_=self.parse([row()]);v=next(iter(records.values()));self.assertEqual(v['spend'],123);self.assertIsNone(v['purchases']);self.assertEqual(v['conversations'],1)
        self.assertEqual(number('1.234,56',True,2,'gasto'),123456)
        with self.assertRaises(ValueError):number('1,234',True,2,'gasto')
    def test_daily_identity_and_duplicates(self):
        records,n=self.parse([row(),row()]);self.assertEqual(len(records),1);self.assertEqual(n,1)
        with self.assertRaisesRegex(ValueError,'conflitante'):self.parse([row(),row(spend='2,00')])
        records,_=self.parse([row(),row(day='2026-09-02')]);self.assertEqual(len(records),2)
    def test_hierarchy_and_grain(self):
        changed=row(ad='3');changed['Identificação do conjunto de anúncios']='4'
        with self.assertRaisesRegex(ValueError,'hierarquia'):self.parse([row(),changed])
        changed=row();changed['Encerramento dos relatórios']='2026-09-02'
        with self.assertRaisesRegex(ValueError,'grão'):self.parse([changed])
    def test_zero_revision_and_hash(self):
        old,_=self.parse([row()]);new,_=self.parse([row(spend='0',conversations='0')]);before=digest(list(old.values()));merged=merge_records(old,new,'2026-09-01','2026-09-01','partial');key=next(iter(old))
        self.assertEqual(merged[key]['spend'],0);self.assertEqual(merged[key]['conversations'],0);self.assertNotEqual(before,digest(list(merged.values())))
    def test_complete_and_partial_scope(self):
        old,_=self.parse([row(),row(day='2026-09-02')]);incoming,_=self.parse([row(spend='0')]);partial=merge_records(old,incoming,'2026-09-01','2026-09-02','partial');self.assertEqual(len(partial),2)
        complete=merge_records(old,incoming,'2026-09-01','2026-09-02','complete');self.assertEqual(len(complete),1)
        outside,_=self.parse([row(day='2026-09-03')]);self.assertEqual(len(merge_records({**old,**outside},incoming,'2026-09-01','2026-09-02','complete')),2)
    def test_mixed_results_not_summed_as_one_kpi(self):
        a=row();b=row(ad='4');b['Indicador de resultados']='profile_visit_view';b['Resultados']='8';b['Conversas por mensagem iniciadas']=''
        records,_=self.parse([a,b]);self.assertEqual(sums(records.values())['conversations'],1)
    def test_public_catalog_uses_latest_name_without_raw_ids(self):
        first=row();latest=row(day='2026-09-02');latest['Nome da campanha']='Campanha atual';latest['Nome do anúncio']='Anúncio atual';latest['Compras']='2';latest['Valor de conversão da compra']='123,45'
        records,_=self.parse([first,latest]);public=public_data(list(records.values()),{'data_hash':'abc','source_export_time':None,'import_time':'2026-09-29','period':{}})
        code=public['rows'][0]['c'];self.assertEqual(public['catalog']['campaign'][code],'Campanha atual')
        self.assertEqual(sum(r['purchase_value'] or 0 for r in public['rows']),12345)
        self.assertNotIn('1',public['catalog']['campaign'])

if __name__=='__main__':unittest.main()
