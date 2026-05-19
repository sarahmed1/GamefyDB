import pandas as pd

real_tx = pd.read_csv('output/powerbi_star/fact_transaction.csv')
syn_tx = pd.read_csv('fact_transaction_synthetic.csv')
combined_tx = pd.concat([real_tx, syn_tx], ignore_index=True)
combined_tx.to_csv('output/powerbi_star/fact_transaction_combined.csv', index=False, encoding='utf-8-sig')

real_sess = pd.read_csv('output/powerbi_star/fact_session.csv')
syn_sess = pd.read_csv('fact_session_synthetic.csv')
combined_sess = pd.concat([real_sess, syn_sess], ignore_index=True)
combined_sess.to_csv('output/powerbi_star/fact_session_combined.csv', index=False, encoding='utf-8-sig')

print('TX combined:', len(combined_tx), 'rows')
print('SESS combined:', len(combined_sess), 'rows')