# ابدأ من هنا — Passive Domain OSINT

هذا مشروع Python + Streamlit مستقل عن موقع GitHub Pages. **لا تضع ملفات Python هذه في مستودع `mdrhoobe.github.io`** بغرض تشغيلها؛ GitHub Pages يستضيف مواقع ثابتة ولا يشغّل خادم Streamlit.

## 1) تجربة المشروع على جهازك Windows

افتح PowerShell داخل مجلد المشروع بعد فك ZIP:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m streamlit run app.py
```

سيفتح Streamlit عادة على `http://localhost:8501`. اضغط **Load synthetic demo (offline)** أولًا. هذا عرض تجريبي صناعي واضح التسمية؛ **ليس تحليلًا حيًا لنطاق**. بعد ذلك جرب نطاقًا واحدًا تسمح لك شروط مصادر البيانات العامة بالاستعلام عنه، وتحقق من حالات نجاح/فشل RDAP وDNS وCT، ثم جرّب تنزيلي JSON وCSV.

إذا لم يظهر المتصفح، افتح الرابط الذي تطبعه Streamlit في الطرفية. إن تعذر تثبيت التبعيات، تحقق من Python 3.11+ والإنترنت وأعد الأمر مع بيئة افتراضية جديدة.

## 2) ما الذي تختبره قبل النشر؟

- نجاح الاختبارات الآلية محليًا، وظهور الواجهة دون أخطاء.
- استخدام تبويب Offline Demo أولًا، مع ظهور تحذير SYNTHETIC.
- التأكد أن بيانات Live تأتي من المصادر العامة وليست من ملفات Fixtures.
- التأكد أن البحث الخاطئ يعطي رسالة واضحة، وأن فشل أي مصدر لا يسقط نتائج البقية.
- تنزيل تقرير JSON وCSV وفتح الملفين.
- عدم نشر صادرات لأي نطاق فعلي أو مفاتيح أو بيانات شخصية عن طريق الخطأ.

## 3) GitHub والمشاريع الأكاديمية

أنشئ مستودعًا **منفصلًا** مثل `mdrhoobe/passive-domain-osint`، ثم من مجلد المشروع:

```powershell
git init
git add .
git status --short
git commit -m "feat: release tested passive domain OSINT research MVP"
git branch -M main
git remote add origin https://github.com/mdrhoobe/passive-domain-osint.git
git push -u origin main
```

**مهم:** أنشئ المستودع أولًا على GitHub، وافحص `git status` قبل أول Commit، وتأكد من عدم إدراج ملفات `.env` أو نتائج مجمعة أو معلومات شخصية. إذا كان `origin` موجودًا أصلًا، فلا تضفه مجددًا. لا تنشئ رسائل Commits متعددة لتوهم بتاريخ تطوير غير حقيقي؛ يمكن استخدام Conventional Commits في التطوير اللاحق.

بعد نجاح التشغيل وأخذ لقطة حقيقية من واجهة المشروع، أضف بطاقة له في موقع البورتفوليو `mdrhoobe.github.io` تشير إلى مستودع المشروع وتشرح المنهجية والقيود والاختبارات.

## 4) حالة التحقق

- اختبارات Python (Offline): **60 ناجحة**.
- التغطية: **92%** لوحدات `src` و`cli.py`.
- تحققنا من Syntax لملف Streamlit، وفحصنا مساري العرض الفارغ وDemo بمحاكاة واجهة، لكن **لم نشغل Streamlit الحقيقي على هذه البيئة** بسبب عدم توافر المكتبة من فهرس الحزم المتاح.
- لم يُجر اختبار API حي من هذه البيئة. شغله محليًا للتأكد من الاتصال.

راجع `README.md` و`docs/REVIEW-AR.md` للتفاصيل.
