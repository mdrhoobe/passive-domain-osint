# تقرير المراجعة وإصلاح مشروع Passive Domain OSINT

## النسخة الأصلية

- أُرسلت كملف RAR بتاريخ 14 نوفمبر 2026. تحتوي على `cli.py` و`src/` و`tests/`، ولا تحتوي على `app.py` الذي كانت وثائقها تشير إليه.
- احتوى `tests/test_collector.py` على `@add_callback` في مواقع لا تتبعها دوال، مما سبب `SyntaxError` في جلسات المستخدم السابقة.
- `src/collector.py` كان يشير إلى RDAP غير موثوق بصياغته الحالية، ولم يُدرج الرد المحمّل في `results`; كما احتوى CT على بيانات وتواريخ ثابتة، واعتمد DNS على PTR بواسطة `dig` (غير ملائم لحالة الاستخدام).
- `src/output.py` احتوى على `self.field_map.get` رغم أن `field_map` دالة، و`export_csv` لم يرجع CSV، و`prepare_results_for_display` يفترض أن RDAP ليس `None`.
- التحقق القديم كان يحذف Unicode وأحرفًا من المدخلات، مما يمكن أن يحوّل النطاق إلى نطاق آخر؛ كما اختلط بفحص شبكة PTR.
- إعدادات التبعيات تضمنت اعتمادًا غير صحيح على `rdapypy`/`certipy` في مراحل سابقة، ووصف README واجهة غير موجودة ونتائج تجريبية مضللة.
- كان اسم مؤلف المشروع في بعض الملفات هو اسم أداة التوليد بدل صاحب المشروع.

## النسخة المصححة v0.2.0

1. تحويل التحقق إلى صيغة حتمية `normalize_domain` دون شبكة، ورفض المدخلات غير المدعومة بدل تنظيفها اعتباطيًا.
2. استخدام IANA RDAP bootstrap واختيار HTTPS المعلن، ثم استخراج معلومات عامة محدودة مع استبعاد بيانات الاتصال الشخصية.
3. استخدام `dnspython` لاستعلامات A وAAAA وMX وNS وTXT للنطاق الواحد.
4. استعلام crt.sh بصيغة JSON، وعرض المطابق تمامًا أو wildcard فقط، دون بيانات وهمية أو تعداد فرعي.
5. إظهار حالات المصادر `ok` و`partial` و`no_data` و`error` بشكل منفصل، ودعم استجابات الشبكة الجزئية وحجم الاستجابة والمهلة.
6. بناء واجهة Streamlit حقيقية في `app.py`، مع نموذج إدخال وتنقل بين المصادر وتصدير JSON/CSV وحالة عرض تجريبي **موسومة بوضوح بأنها صناعية**.
7. إنشاء اختبارات Offline، مع منع اتصالات الشبكة في جميع الاختبارات؛ وإضافة GitHub Actions للاختبار على Python 3.11/3.12/3.13.
8. تحسين README وSECURITY.md والاعتمادات والترخيص و`.gitignore`.

## التحقق الذي أُجري فعليًا

- `python -m compileall -q src cli.py app.py tests`: نجاح.
- `python -m pytest -q`: **60 passed**.
- `python -m pytest --cov=src --cov=cli --cov-report=term-missing -q`: **92%** تغطية مشتركة للوحدات الأساسية وCLI.
- `python cli.py validate https://Example.com`: يعرض `example.com` دون شبكة.
- لم أتحقق من استجابة حيّة لمصادر IANA/RDAP/crt.sh/DNS داخل هذه البيئة؛ الاختبارات استعملت Fixtures فقط.
- لم ينجح تثبيت مكتبة Streamlit في بيئة التنفيذ الحالية (غير متاحة في فهرس الحزم المتاح)، لذا اختبرت صياغة واجهة `app.py` ولم أشغّل تجربة تفاعل متصفح حقيقية. يجب اختبارها على Windows محليًا.

## تعليمات Windows

```powershell
cd "$HOME\Documents\Scholarship-Projects\passive-domain-osint"
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m streamlit run app.py
```

بعد تشغيل الواجهة جرّب أولًا **Load synthetic demo (offline)**؛ ثم اختبر موقعًا تسمح قوانين/شروط الاستخدام بجمع بياناته العامة. لا ترفع أي نتائج حقيقية أو بيانات خاصة إلى GitHub. أضف رسائل Conventional Commits بعد مراجعة الملفّات، ولا تنشئ تاريخًا وهميًا للتعديلات.

**حالة النشر:** نسخة قابلة للاختبار المحلي والنشر كمستودع كود، وليست خدمة عامة تم التحقق منها ضد المصادر الحية والمتصفحات حتى الآن.
