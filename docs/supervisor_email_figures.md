# Email to supervisor

---

**Subject:** PFE progress — revenue and session-volume forecasts (Holt-Winters added)

Dear Sir,

I hope this message finds you well.

Since our last exchange, I have added **Holt-Winters** as a fourth model
to the forecasting protocol for monthly revenue and monthly session
volume, alongside Prophet, SARIMA and XGBoost. The Overleaf report has
been updated with the corresponding subsection and new figures.

Please find attached the eight figures (4 models × 2 series). The
**main goal of this email is to share the figures**, so I am keeping
the description brief:

- `forecast_monthly_revenue_holtwinters.png`, `..._sarima.png`,
  `..._xgboost.png`, `..._prophet.png` — monthly revenue forecasts.
- `forecast_monthly_sessions_holtwinters.png`, `..._sarima.png`,
  `..._xgboost.png`, `..._prophet.png` — monthly session-volume
  forecasts.

On both series Holt-Winters comes out as the best model on wMAPE,
followed by XGBoost, then SARIMA, then Prophet. The green dashed
vertical line on each figure marks the boundary between the synthetic
backfill (needed so SARIMA / Holt-Winters see enough seasonal cycles)
and the real data; metrics are computed only on the real test window.

Please let me know if you would like the figure descriptions in French,
or if you would prefer a short meeting to walk through the results
together.

Thank you in advance for your time.

Best regards,
Sarra Mediouni
