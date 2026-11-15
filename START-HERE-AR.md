# دليل الاستخدام — Passive Domain OSINT

المشروع منشور على GitHub:
https://github.com/mdrhoobe/passive-domain-osint

هذه أداة Python وStreamlit مستقلة عن موقع Portfolio. لا يمكن تشغيل خادم Streamlit مباشرة داخل GitHub Pages.

## البدء على Windows (PowerShell)

```powershell
git clone https://github.com/mdrhoobe/passive-domain-osint.git
cd passive-domain-osint
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m streamlit run app.py
```

إذا كانت نسختك من Python مختلفة (3.12 أو 3.13)، استبدل أمر إنشاء البيئة بـ `python -m venv .venv`.

## الاستخدام والنتائج

اضغط **Load synthetic demo (offline)** لاستعراض الواجهة ببيانات تجريبية واضحة التسمية، دون الاتصال بمصادر خارجية.

لجمع بيانات حقيقية، أدخل نطاقًا واحدًا، ثم افتح أقسام RDAP وDNS وCertificate Transparency. يمكن تنزيل بيانات JSON وCSV من تبويب **Export / Methodology**. البيانات عامة وقد تكون ناقصة أو غير متاحة بسبب القيود والمهلات.

**لا تنشر تقارير لنطاقات حقيقية قبل مراجعة البيانات واحترام شروط المصادر.**

## التحقق

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\live_smoke.py
```

الاختبارات الأولى تعمل Offline. الاختبار الثاني يرسل طلبات عامة فعلية للنطاق المحجوز `example.com`، ويفحص إمكانية قراءة JSON وCSV ويعرض الحالة الحقيقية لكل مصدر. لا تعني نتيجة نجاح واحدة أن جميع مصادر الشبكة تعمل.

تولد GitHub Actions لقطة للواجهة الحقيقية في متصفح Chromium باستخدام Synthetic Demo، وتتحقق أيضًا من زرَي تنزيل JSON وCSV.

للمزيد اقرأ [README.md](README.md) و[SECURITY.md](SECURITY.md).
