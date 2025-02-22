
app = Flask(__name__)
app.secret_key = os.urandom(24)

# MongoDB setup
client = MongoClient('mongodb://ahmed:Ma_213243@cluster0-shard-00-00.sdxls.mongodb.net:27017,cluster0-shard-00-01.sdxls.mongodb.net:27017,cluster0-shard-00-02.sdxls.mongodb.net:27017/?ssl=true&replicaSet=atlas-qmfg4n-shard-0&authSource=admin&retryWrites=true&w=majority&appName=Cluster0')
db = client['card_validator']
codes_col = db['codes']
ips_col = db['ips']
settings_col = db['settings']
admin_collection = db["admin"]
if not admin_collection.find_one({"_id": "admin"}):
    admin_collection.insert_one({"_id": "admin", "username": "saoud", "password": "saoud12"})

# إنشاء الإعدادات الافتراضية إن لم تكن موجودة
if not settings_col.find_one({'name': 'main'}):
    settings_col.insert_one({
        'name': 'main',
        'validator1_active': True,
        'validator2_active': True
    })

###############################################
# دوال مساعدة
###############################################

def validate_card_format(card):
    """
    دالة بسيطة للتحقق من تنسيق البطاقة (رقم|شهر|سنة|CVV).
    مثال: 1234123412341234|12|2025|123
    """
    pattern = r'^\d{13,19}\|\d{1,2}\|\d{2,4}\|\d{3,4}$'
    return bool(re.match(pattern, card.strip()))

def dummy_check_card(card, validator_type=1):
    """
    دالة وهمية لتوزيع النتائج بشكل عشوائي.
    في مشروعك الحقيقي، يمكنك الاتصال بـ API خارجي أو استخدام أي منطق تريده.
    """
    # للتمييز بين الفاليديتور الأول والثاني
    # validator_type=1 -> (Approved, CCN, Declined)
    # validator_type=2 -> (Charged, Approved, CCN, Declined)
    results_pool = []
    if validator_type == 1:
        # ثلاثة احتمالات
        results_pool = ["approved", "ccn", "declined"]
    else:
        # أربعة احتمالات
        results_pool = ["charged", "approved", "ccn", "declined"]
    return random.choice(results_pool)

def has_valid_code_for_ip(ip):
    """
    يتحقق ما إذا كان الـ IP لديه كود صالح (لم تنتهِ مدته).
    """
    record = ips_col.find_one({'ip': ip})
    if record:
        # إذا انتهت مدة الكود، نحذفه ونرجع False
        if record['expires_at'] < datetime.now():
            ips_col.delete_one({'ip': ip})
            return False
        return True
    return False

###############################################
# المسارات (Routes)
###############################################

@app.route('/')
def home():
    """
    الصفحة الرئيسية: اختيار الفاليديتور1 أو الفاليديتور2.
    """
    settings = settings_col.find_one({'name': 'main'})
    validator1_active = settings['validator1_active']
    validator2_active = settings['validator2_active']
    return render_template_string(HOME_TEMPLATE,
                                  validator1_active=validator1_active,
                                  validator2_active=validator2_active)
def validate_card_format(card):
    """التحقق من تنسيق البطاقة"""
    pattern = r'^\d{15,16}\|\d{1,2}\|\d{2,4}\|\d{3,4}$'
    return re.match(pattern, card) is not None

def dummy_check_card(card, validator_type=2):
    """محاكاة عملية فحص البطاقة (للاختبار)"""
    time.sleep(0.5)  # محاكاة زمن الانتظار
    
    # نماذج نتائج عشوائية
    rand_num = random.randint(1, 100)
    
    if validator_type == 1:
        return 'charged' if rand_num > 50 else 'declined'
    else:
        if rand_num > 80:
            return 'approved'
        elif rand_num > 60:
            return 'ccn'
        else:
            return 'declined'

# حالة التحكم في الفحص (يجب وضعها في أعلى الملف)
validation_active = False
stop_requested = False

@app.route('/validator1', methods=['GET', 'POST'])
def validator1():
    global validation_active, stop_requested
    
    settings = settings_col.find_one({'name': 'main'}) or {'validator1_active': True}
    
    if not settings.get('validator1_active', True):
        return "<h1 style='color:red;text-align:center;margin-top:50px;'>Validator 1 معطّل حالياً</h1>"

    if request.method == 'GET':
        return render_template_string(VALIDATOR1_TEMPLATE)
    
    cards_text = request.form.get('cards', '').strip()
    cards_list = [c.strip() for c in cards_text.split('\n') if c.strip()]
    
    validation_active = True
    stop_requested = False
    
    def generate():
        global validation_active, stop_requested
        
        yield "data: {}\n\n".format(json.dumps({'type': 'init'}))
        
        results = {'approved': [], 'ccn': [], 'declined': []}
        for card in cards_list:
            if not validation_active or stop_requested:
                break
                
            if not validate_card_format(card):
                continue
                
            result = dummy_check_card(card)
            results[result].append(card)
            
            yield "data: {}\n\n".format(json.dumps({
                'type': 'update',
                'category': result,
                'card': card,
                'counts': {
                    'approved': len(results['approved']),
                    'ccn': len(results['ccn']),
                    'declined': len(results['declined'])
                }
            }))
        
        validation_active = False
        yield "data: {}\n\n".format(json.dumps({
            'type': 'complete',
            'stopped': stop_requested
        }))
    
    return Response(generate(), mimetype='text/event-stream')

@app.route('/stop_validation')
def stop_validation():
    global stop_requested
    stop_requested = True
    return json.dumps({'status': 'success'})
validation2_active = False
stop2_requested = False

VALIDATOR2_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>Validator 2 (مدفوع)</title>
    <style>
        /* تنسيقات عامة مشابهة للنظام المستخدم في Validator1 */
        body {
            background: #f4f4f4;
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
        }
        .container {
            background: #fff;
            padding: 20px 30px;
            border-radius: 8px;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
            width: 90%;
            max-width: 800px;
            text-align: center;
        }
        h1 {
            margin-bottom: 20px;
            color: #333;
        }
        textarea {
            width: 100%;
            height: 120px;
            padding: 10px;
            font-size: 16px;
            border: 1px solid #ccc;
            border-radius: 4px;
            margin-bottom: 20px;
            resize: vertical;
        }
        button.btn-check {
            padding: 10px 20px;
            background: #3498db;
            border: none;
            color: #fff;
            font-size: 16px;
            border-radius: 4px;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        button.btn-check.btn-stop {
            background: #dc3545;
        }
        button.btn-check:hover {
            opacity: 0.9;
        }
        /* أقسام النتائج */
        .results {
            margin-top: 20px;
            text-align: left;
        }
        .category {
            margin-bottom: 20px;
            border: 1px solid #ddd;
            border-radius: 4px;
            overflow: hidden;
        }
        .category-header {
            padding: 10px;
            background: #f8f9fa;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .category-header h3 {
            margin: 0;
            font-size: 18px;
        }
        .category-header .buttons button {
            margin-left: 10px;
            padding: 5px 10px;
            border: none;
            border-radius: 3px;
            cursor: pointer;
        }
        .toggle-btn {
            background: #6c757d;
            color: white;
        }
        .copy-btn {
            background: #28a745;
            color: white;
        }
        .cards-list {
            padding: 10px;
            background: white;
            font-family: monospace;
            white-space: pre-wrap;
            max-height: 200px;
            overflow-y: auto;
        }
        /* ألوان التصنيفات */
        .charged .category-header { border-left: 4px solid #27ae60; }
        .approved .category-header { border-left: 4px solid #27ae60; }
        .ccn .category-header { border-left: 4px solid #ffc107; }
        .declined .category-header { border-left: 4px solid #e74c3c; }
        /* مؤشر التحميل */
        #loading {
            display: none;
            margin: 20px 0;
            color: #3498db;
            animation: pulse 1.5s infinite;
        }
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
    </style>
</head>
<body>
<div class="container">
    <h1>Validator 2 (مدفوع)</h1>
    <form id="validatorForm" onsubmit="startValidation(event)">
        <textarea name="cards" placeholder="أدخل البطاقات بصيغة:
CARD|MONTH|YEAR|CVV
مثال: 4701300000244481|08|2026|350" required></textarea>
        <br>
        <button class="btn-check" type="submit" id="submitBtn">ابدأ الفحص</button>
    </form>
    <div id="loading">جاري المعالجة... ⌛</div>
    <div class="results" id="results" style="display:none;">
        <div class="category charged">
            <div class="category-header">
                <h3>Charged (<span id="charged-count">0</span>)</h3>
                <div class="buttons">
                    <button type="button" class="toggle-btn" onclick="toggleSection('charged-list')">إخفاء</button>
                    <button type="button" class="copy-btn" onclick="copySection('charged-list')">نسخ</button>
                </div>
            </div>
            <div class="cards-list" id="charged-list"></div>
        </div>
        <div class="category approved">
            <div class="category-header">
                <h3>Approved (<span id="approved-count">0</span>)</h3>
                <div class="buttons">
                    <button type="button" class="toggle-btn" onclick="toggleSection('approved-list')">إخفاء</button>
                    <button type="button" class="copy-btn" onclick="copySection('approved-list')">نسخ</button>
                </div>
            </div>
            <div class="cards-list" id="approved-list"></div>
        </div>
        <div class="category ccn">
            <div class="category-header">
                <h3>CCN (<span id="ccn-count">0</span>)</h3>
                <div class="buttons">
                    <button type="button" class="toggle-btn" onclick="toggleSection('ccn-list')">إخفاء</button>
                    <button type="button" class="copy-btn" onclick="copySection('ccn-list')">نسخ</button>
                </div>
            </div>
            <div class="cards-list" id="ccn-list"></div>
        </div>
        <div class="category declined">
            <div class="category-header">
                <h3>Declined (<span id="declined-count">0</span>)</h3>
                <div class="buttons">
                    <button type="button" class="toggle-btn" onclick="toggleSection('declined-list')">إخفاء</button>
                    <button type="button" class="copy-btn" onclick="copySection('declined-list')">نسخ</button>
                </div>
            </div>
            <div class="cards-list" id="declined-list"></div>
        </div>
    </div>
    <a class="back-link" href="/" style="display:block; margin-top:20px; text-align:center;">عودة للرئيسية</a>
</div>
<script>
    let isProcessing = false;
    let controller = null;

    function startValidation(e) {
        e.preventDefault();
        if (isProcessing) {
            stopValidation();
            return;
        }
        const form = e.target;
        const resultsDiv = document.getElementById('results');
        const loadingDiv = document.getElementById('loading');
        const submitBtn = document.getElementById('submitBtn');

        // إعادة تعيين النتائج
        ['charged', 'approved', 'ccn', 'declined'].forEach(cat => {
            document.getElementById(`${cat}-list`).innerHTML = '';
            document.getElementById(`${cat}-count`).textContent = '0';
        });
        resultsDiv.style.display = 'block';

        isProcessing = true;
        submitBtn.textContent = 'إيقاف الفحص';
        submitBtn.classList.add('btn-stop');
        loadingDiv.style.display = 'block';

        controller = new AbortController();

        fetch('/validator2', {
            method: 'POST',
            body: new FormData(form),
            signal: controller.signal
        }).then(response => {
            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            function process({done, value}) {
                if (done) {
                    finishProcessing();
                    return;
                }
                const dataChunk = decoder.decode(value);
                dataChunk.split("\\n\\n").forEach(line => {
                    if (line.startsWith("data: ")) {
                        try {
                            const data = JSON.parse(line.slice(6));
                            handleStreamData(data);
                        } catch(e) {
                            console.error("خطأ في تحليل البيانات:", e);
                        }
                    }
                });
                return reader.read().then(process);
            }
            return reader.read().then(process);
        }).catch(err => {
            if (err.name === 'AbortError') {
                finishProcessing(true);
            }
        });
    }

    function stopValidation() {
        if (controller) {
            controller.abort();
        }
        fetch('/stop_validation2');
        finishProcessing(true);
    }

    function finishProcessing(stopped = false) {
        const submitBtn = document.getElementById('submitBtn');
        const loadingDiv = document.getElementById('loading');
        isProcessing = false;
        submitBtn.textContent = 'ابدأ الفحص';
        submitBtn.classList.remove('btn-stop');
        loadingDiv.style.display = 'none';
        if (stopped) {
            showToast('تم إيقاف الفحص بنجاح', 'red');
        }
    }

    function handleStreamData(data) {
        if (data.type === 'update') {
            const category = data.category; // charged, approved, ccn, declined
            const list = document.getElementById(category + "-list");
            const countSpan = document.getElementById(category + "-count");
            const newItem = document.createElement('div');
            newItem.textContent = data.card;
            list.appendChild(newItem);
            // تحديث العد لجميع التصنيفات
            document.getElementById("charged-count").textContent = data.counts.charged;
            document.getElementById("approved-count").textContent = data.counts.approved;
            document.getElementById("ccn-count").textContent = data.counts.ccn;
            document.getElementById("declined-count").textContent = data.counts.declined;
            list.scrollTop = list.scrollHeight;
        }
        // يمكن إضافة معالجات لأنواع أخرى مثل init أو complete إذا دعت الحاجة
    }

    function toggleSection(id) {
        const section = document.getElementById(id);
        section.style.display = (section.style.display === "none") ? "block" : "none";
    }

    function copySection(id) {
        const text = document.getElementById(id).innerText;
        navigator.clipboard.writeText(text)
            .then(() => showToast('تم النسخ بنجاح ✅', 'green'))
            .catch(() => showToast('خطأ في النسخ ❌', 'red'));
    }

    function showToast(message, color) {
        const toast = document.createElement('div');
        toast.style = `
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: ${color};
            color: white;
            padding: 12px 24px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            z-index: 1000;
            animation: slideUp 0.3s ease;
        `;
        toast.textContent = message;
        document.body.appendChild(toast);
        setTimeout(() => { toast.remove(); }, 3000);
    }
</script>
</body>
</html>
"""

@app.route('/validator2', methods=['GET', 'POST'])
def validator2():
    global validation2_active, stop2_requested
    # التحقق من تفعيل الـ Validator2 في الإعدادات
    settings = settings_col.find_one({'name': 'main'})
    if not settings.get('validator2_active', False):
        return "<h1 style='color:red;text-align:center;margin-top:50px;'>Validator 2 معطّل حالياً</h1>"

    user_ip = request.remote_addr
    if not has_valid_code_for_ip(user_ip):
        return redirect(url_for('enter_code'))

    if request.method == 'GET':
        return render_template_string(VALIDATOR2_TEMPLATE)

    # في حالة الـ POST: نستخدم بث SSE لتحديث النتائج بشكل مباشر
    cards_text = request.form.get('cards', '').strip()
    cards_list = [c.strip() for c in cards_text.split('\n') if c.strip()]
    validation2_active = True
    stop2_requested = False
    results = {'charged': [], 'approved': [], 'ccn': [], 'declined': []}

    def generate():
        global validation2_active, stop2_requested
        # إرسال حدث البداية
        yield "data: {}\n\n".format(json.dumps({'type': 'init'}))
        for card in cards_list:
            if not validation2_active or stop2_requested:
                break
            if not validate_card_format(card):
                continue
            result = dummy_check_card(card, validator_type=2)
            results[result].append(card)
            yield "data: {}\n\n".format(json.dumps({
                'type': 'update',
                'category': result,
                'card': card,
                'counts': {
                    'charged': len(results['charged']),
                    'approved': len(results['approved']),
                    'ccn': len(results['ccn']),
                    'declined': len(results['declined'])
                }
            }))
        validation2_active = False
        yield "data: {}\n\n".format(json.dumps({
            'type': 'complete',
            'stopped': stop2_requested
        }))

    return Response(generate(), mimetype='text/event-stream')

@app.route('/stop_validation2')
def stop_validation2():
    global stop2_requested
    stop2_requested = True
    return json.dumps({'status': 'success'})


@app.route('/code', methods=['GET', 'POST'])
def enter_code():
    """
    صفحة إدخال الكود للـ Validator2.
    يتحقق من وجود الكود في قاعدة البيانات وصلاحيته.
    إذا كان صالحاً، يربط الـ IP بهذا الكود حتى انتهاء مدته.
    """
    if request.method == 'POST':
        code_entered = request.form.get('code', '').strip()
        # ابحث عن الكود في قاعدة البيانات
        code_doc = codes_col.find_one({'code': code_entered})
        if code_doc:
            # تحقّق من انتهاء الصلاحية
            if code_doc['expires_at'] < datetime.now():
                # حُذِف أو انتهى
                codes_col.delete_one({'_id': code_doc['_id']})
                return render_template_string(CODE_TEMPLATE, error="انتهت صلاحية الكود.")
            # تحقّق هل الكود مستخدم من IP آخر
            if 'ip' in code_doc and code_doc['ip'] != request.remote_addr:
                return render_template_string(CODE_TEMPLATE, error="هذا الكود مستخدم من IP آخر.")
            # اربط الكود بالـ IP الحالي (إذا لم يكن مرتبطاً)
            codes_col.update_one({'_id': code_doc['_id']}, {'$set': {'ip': request.remote_addr}})
            # خزّن في مجموعة ips أيضاً (للبحث السريع)
            ips_col.update_one(
                {'ip': request.remote_addr},
                {'$set': {'code': code_doc['code'], 'expires_at': code_doc['expires_at']}},
                upsert=True
            )
            return redirect(url_for('validator2'))
        else:
            return render_template_string(CODE_TEMPLATE, error="الكود غير صحيح أو غير موجود.")
    return render_template_string(CODE_TEMPLATE)

@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == "POST":
        admin = admin_collection.find_one({"_id": "admin"})
        if request.form["username"] == admin["username"] and request.form["password"] == admin["password"]:
            session["logged_in"] = True
            return redirect(url_for("admin_dashboard"))
    return render_template_string(ADMIN_LOGIN_TEMPLATE)
@app.route('/admin/dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    """
    لوحة تحكم الأدمن:
      - توليد الأكواد (مع مدة صلاحية بالساعات).
      - تفعيل/إيقاف كل فاليديتور.
      - عرض الأكواد النشطة.
    """
    if not session.get("logged_in"):
        return redirect(url_for("admin_login"))
    settings = settings_col.find_one({'name': 'main'})
    if request.method == 'POST':
        if 'generate_code' in request.form:
            duration_hours = int(request.form.get('duration', '1'))
            new_code = os.urandom(4).hex()  # توليد كود عشوائي
            expires_at = datetime.now() + timedelta(hours=duration_hours)
            codes_col.insert_one({
                'code': new_code,
                'expires_at': expires_at
            })
        elif 'toggle_validator' in request.form:
            validator = request.form.get('validator')  # 'validator1' or 'validator2'
            status = request.form.get('status') == 'true'
            settings_col.update_one({'name': 'main'}, {'$set': {f'{validator}_active': status}})

    # جلب الأكواد النشطة حالياً
    active_codes = list(codes_col.find({'expires_at': {'$gt': datetime.now()}}))
    settings = settings_col.find_one({'name': 'main'})

    return render_template_string(
        ADMIN_DASHBOARD_TEMPLATE,
        active_codes=active_codes,
        validator1_active=settings['validator1_active'],
        validator2_active=settings['validator2_active']
    )

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('home'))

###############################################
# القوالب المضمّنة (HTML + CSS)
###############################################

HOME_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>الرئيسية</title>
    <style>
        /* Reset عام */
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            background: linear-gradient(135deg, #1a1a1a, #333);
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            color: #fff;
            text-align: center;
            height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }
        h1 {
            font-size: 3rem;
            margin-bottom: 20px;
            text-shadow: 2px 2px 8px rgba(0,0,0,0.7);
        }
        .container {
            padding: 30px 40px;
            background: rgba(0, 0, 0, 0.6);
            border-radius: 10px;
            box-shadow: 0 0 20px rgba(0,0,0,0.8);
        }
        p {
            font-size: 1.2rem;
            margin-bottom: 30px;
        }
        .btn {
            display: inline-block;
            padding: 15px 30px;
            margin: 10px;
            background: #555;
            color: #fff;
            text-decoration: none;
            border-radius: 50px;
            border: none;
            transition: background 0.3s ease, transform 0.3s ease;
        }
        .btn:hover {
            background: #777;
            transform: scale(1.05);
        }
        .disabled {
            opacity: 0.5;
            pointer-events: none;
        }
    </style>
</head>
<body>
    <h1>مرحباً بك</h1>
    <div class="container">
        <p>اختر الفاحص:</p>
        <a href="{{ url_for('validator1') }}" class="btn {% if not validator1_active %}disabled{% endif %}">Validator 1</a>
        <a href="{{ url_for('validator2') }}" class="btn {% if not validator2_active %}disabled{% endif %}">Validator 2</a>
    </div>
</body>
</html>
"""


# القالب مع جميع التنسيقات والدوال
VALIDATOR1_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>Validator 1 (مجاني)</title>
<style>
    /* تنسيق عام */
    body {
        background: #f4f4f4;
        font-family: Arial, sans-serif;
        margin: 0;
        padding: 0;
        display: flex;
        justify-content: center;
        align-items: center;
        min-height: 100vh;
    }

    .container {
        background: #fff;
        padding: 20px 30px;
        border-radius: 8px;
        box-shadow: 0 0 10px rgba(0,0,0,0.1);
        width: 90%;
        max-width: 800px;
        text-align: center;
    }

    h1 {
        margin-bottom: 20px;
        color: #333;
    }

    textarea {
        width: 100%;
        height: 120px;
        padding: 10px;
        font-size: 16px;
        border: 1px solid #ccc;
        border-radius: 4px;
        margin-bottom: 20px;
        resize: vertical;
    }

    button.btn-check {
        padding: 10px 20px;
        background: #28a745;
        border: none;
        color: #fff;
        font-size: 16px;
        border-radius: 4px;
        cursor: pointer;
        transition: all 0.3s ease;
    }

    button.btn-check.btn-stop {
        background: #dc3545;
    }

    button.btn-check:hover {
        opacity: 0.9;
    }

    /* أقسام النتائج */
    .results {
        margin-top: 20px;
        text-align: left;
    }

    .category {
        margin-bottom: 20px;
        border: 1px solid #ddd;
        border-radius: 4px;
        overflow: hidden;
    }

    .category-header {
        padding: 10px;
        background: #f8f9fa;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .category-header h3 {
        margin: 0;
        font-size: 18px;
    }

    .category-header .buttons button {
        margin-left: 10px;
        padding: 5px 10px;
        border: none;
        border-radius: 3px;
        cursor: pointer;
    }

    .toggle-btn {
        background: #6c757d;
        color: white;
    }

    .copy-btn {
        background: #28a745;
        color: white;
    }

    .cards-list {
        padding: 10px;
        background: white;
        font-family: monospace;
        white-space: pre-wrap;
        max-height: 200px;
        overflow-y: auto;
    }

    .card-item {
        padding: 8px;
        margin: 4px 0;
        background: #f8f9fa;
        border-radius: 4px;
        animation: cardAppear 0.3s ease;
    }

    @keyframes cardAppear {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }

    /* ألوان التصنيفات */
    .approved .category-header { border-left: 4px solid #28a745; }
    .ccn .category-header { border-left: 4px solid #ffc107; }
    .declined .category-header { border-left: 4px solid #dc3545; }
    .invalid .category-header { border-left: 4px solid #6c757d; }

    /* مؤشر التحميل */
    #loading {
        display: none;
        margin: 20px 0;
        color: #3498db;
        animation: pulse 1.5s infinite;
    }

    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.5; }
        100% { opacity: 1; }
    }
</style>
<style>
    /* إضافة أنيميشن للتحميل */
    #loading {
        display: none;
        margin: 20px 0;
        color: #3498db;
        animation: pulse 1.5s infinite;
    }

    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.5; }
        100% { opacity: 1; }
    }

    /* أزرار التحكم */
    .btn-check {
        transition: all 0.3s ease !important;
    }

    .btn-stop {
        background: #dc3545 !important;
        padding: 10px 25px !important;
        transform: scale(1.05);
    }

    .btn-stop:hover {
        background: #c82333 !important;
        transform: scale(1.08);
    }

    /* تأثيرات للبطاقات الجديدة */
    .cards-list div:last-child {
        animation: slideIn 0.3s ease;
    }

    @keyframes slideIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
</style>
<div class="container">
    <h1>Validator 1 (مجاني)</h1>
    <form id="validatorForm" onsubmit="startValidation(event)">
        <textarea name="cards" placeholder="CARD|MONTH|YEAR|CVV\nمثال: 4916801234567890|12|2025|123" required></textarea>
        <br>
<button class="btn-check" type="submit" id="submitBtn">ابدأ الفحص</button>
    </form>
    <div id="loading">جاري المعالجة... ⌛</div>
    <div class="results" id="results">
        <div class="category approved">
            <div class="category-header">
                <h3>Approved (<span id="approved-count">0</span>)</h3>
                <div class="buttons">
                    <button type="button" class="toggle-btn" onclick="toggleSection('approved-list')">إخفاء</button>
                    <button type="button" class="copy-btn" onclick="copySection('approved-list')">نسخ</button>
                </div>
            </div>
            <div class="cards-list" id="approved-list"></div>
        </div>
        <div class="category ccn">
            <div class="category-header">
                <h3>CCN (<span id="ccn-count">0</span>)</h3>
                <div class="buttons">
                    <button type="button" class="toggle-btn" onclick="toggleSection('ccn-list')">إخفاء</button>
                    <button type="button" class="copy-btn" onclick="copySection('ccn-list')">نسخ</button>
                </div>
            </div>
            <div class="cards-list" id="ccn-list"></div>
        </div>
        <div class="category declined">
            <div class="category-header">
                <h3>Declined (<span id="declined-count">0</span>)</h3>
                <div class="buttons">
                    <button type="button" class="toggle-btn" onclick="toggleSection('declined-list')">إخفاء</button>
                    <button type="button" class="copy-btn" onclick="copySection('declined-list')">نسخ</button>
                </div>
            </div>
            <div class="cards-list" id="declined-list"></div>
        </div>
    </div>
    <a class="back-link" href="/" style="display: block; margin-top: 20px; text-align: center;">عودة للرئيسية</a>
</div>

<script>
    let isProcessing = false;
    let controller = null;

    function startValidation(e) {
        e.preventDefault();
        if (isProcessing) {
            stopValidation();
            return;
        }
        
        const form = e.target;
        const resultsDiv = document.getElementById('results');
        const loadingDiv = document.getElementById('loading');
        const submitBtn = document.getElementById('submitBtn');
        
        // تغيير حالة الزر
        isProcessing = true;
        submitBtn.textContent = 'إيقاف الفحص';
        submitBtn.classList.add('btn-stop');
        
        // إعادة تعيين النتائج
        
        loadingDiv.style.display = 'block';
        ['approved', 'ccn', 'declined'].forEach(cat => {
            document.getElementById(`${cat}-list`).innerHTML = '';
            document.getElementById(`${cat}-count`).textContent = '0';
        });

        controller = new AbortController();
        
        fetch('/validator1', {
            method: 'POST',
            body: new FormData(form),
            signal: controller.signal
        }).then(response => {
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            
            function process({done, value}) {
                if (done) {
                    finishProcessing();
                    return;
                }
                
                const dataChunk = decoder.decode(value);
                dataChunk.split('\\n\\n').forEach(line => {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));
                            handleStreamData(data);
                        } catch(e) {
                            console.error('خطأ في تحليل البيانات:', e);
                        }
                    }
                });
                
                return reader.read().then(process);
            }
            
            return reader.read().then(process);
        }).catch(err => {
            if (err.name === 'AbortError') {
                finishProcessing(true);
            }
        });
    }

    function stopValidation() {
        if (controller) {
            controller.abort();
        }
        fetch('/stop_validation');
        finishProcessing(true);
    }

    function finishProcessing(stopped = false) {
        const submitBtn = document.getElementById('submitBtn');
        const loadingDiv = document.getElementById('loading');
        const resultsDiv = document.getElementById('results');
        
        isProcessing = false;
        submitBtn.textContent = 'ابدأ الفحص';
        submitBtn.classList.remove('btn-stop');
        loadingDiv.style.display = 'none';
        
        if (stopped) {
            resultsDiv.style.display = 'block';
            showToast('تم إيقاف الفحص بنجاح', 'red');
        }
    }

    function handleStreamData(data) {
        switch(data.type) {
            case 'update':
                const list = document.getElementById(`${data.category}-list`);
                const countSpan = document.getElementById(`${data.category}-count`);
                
                const newItem = document.createElement('div');
                newItem.textContent = data.card;
                list.appendChild(newItem);
                
                countSpan.textContent = data.counts[data.category];
                list.scrollTop = list.scrollHeight;
                break;
        }
    }

    function toggleSection(id) {
        const section = document.getElementById(id);
        section.style.display = section.style.display === 'none' ? 'block' : 'none';
    }

    function copySection(id) {
        const text = document.getElementById(id).innerText;
        navigator.clipboard.writeText(text)
            .then(() => showToast('تم النسخ بنجاح ✅', 'green'))
            .catch(() => showToast('خطأ في النسخ ❌', 'red'));
    }

    function showToast(message, color) {
        const toast = document.createElement('div');
        toast.style = `
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: ${color};
            color: white;
            padding: 12px 24px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            z-index: 1000;
            animation: slideUp 0.3s ease;
        `;
        toast.textContent = message;
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.remove();
        }, 3000);
    }
</script>
</body>
</html>
"""


CODE_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>إدخال الكود</title>
    <style>
        body {
            background: #222;
            color: #fff;
            font-family: sans-serif;
            margin: 0; padding: 0;
            display: flex; 
            justify-content: center; 
            align-items: center; 
            height: 100vh;
        }
        .box {
            background: #333;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            width: 300px;
        }
        input[type=text] {
            width: 80%%;
            padding: 10px;
            margin: 10px 0;
            border: none;
            outline: none;
            border-radius: 5px;
        }
        input[type=submit] {
            padding: 10px 20px;
            background: #e74c3c;
            color: #fff;
            border: none;
            border-radius: 5px;
            cursor: pointer;
        }
        .error {
            color: #ff5555;
        }
        .back {
            margin-top: 10px;
            display: inline-block;
            text-decoration: none;
            color: #aaa;
        }
    </style>
</head>
<body>
    <div class="box">
        <h2>أدخل الكود</h2>
        {% if error %}
        <p class="error">{{ error }}</p>
        {% endif %}
        <form method="POST">
            <input type="text" name="code" placeholder="الكود" required>
            <br>
            <input type="submit" value="تأكيد">
        </form>
        <a class="back" href="{{ url_for('home') }}">عودة للرئيسية</a>
    </div>
</body>
</html>
"""

ADMIN_LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>تسجيل دخول الأدمن</title>
    <style>
        body {
            background: #222;
            color: #fff;
            font-family: sans-serif;
            margin: 0; padding: 0;
            display: flex; 
            justify-content: center; 
            align-items: center; 
            height: 100vh;
        }
        .box {
            background: #333;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            width: 300px;
        }
        input[type=text], input[type=password] {
            width: 80%%;
            padding: 10px;
            margin: 10px 0;
            border: none;
            outline: none;
            border-radius: 5px;
        }
        input[type=submit] {
            padding: 10px 20px;
            background: #e74c3c;
            color: #fff;
            border: none;
            border-radius: 5px;
            cursor: pointer;
        }
        .error {
            color: #ff5555;
        }
    </style>
</head>
<body>
    <div class="box">
        <h2>تسجيل دخول الأدمن</h2>
        {% if error %}
        <p class="error">{{ error }}</p>
        {% endif %}
        <form method="POST">
            <input type="text" name="username" placeholder="اسم المستخدم" required><br>
            <input type="password" name="password" placeholder="كلمة المرور" required><br>
            <input type="submit" value="دخول">
        </form>
    </div>
</body>
</html>
"""

ADMIN_DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>لوحة تحكم الأدمن</title>
    <style>
        body {
            background: #222;
            color: #fff;
            font-family: sans-serif;
            margin: 0; padding: 0;
        }
        .container {
            width: 90%%;
            margin: auto;
            padding: 20px;
        }
        h1 {
            text-align: center;
            margin-top: 20px;
        }
        .section {
            background: #333;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        label {
            display: inline-block;
            width: 120px;
        }
        input[type=number] {
            width: 60px;
        }
        .btn {
            padding: 8px 15px;
            background: #e74c3c;
            color: #fff;
            border: none;
            border-radius: 5px;
            margin-left: 10px;
            cursor: pointer;
        }
        table {
            width: 100%%;
            border-collapse: collapse;
            margin-top: 10px;
        }
        th, td {
            border: 1px solid #444;
            padding: 8px;
            text-align: center;
        }
        .switch-btn {
            margin-left: 10px;
            padding: 5px 10px;
            background: #555;
            color: #fff;
            border-radius: 4px;
            cursor: pointer;
            display: inline-block;
        }
        .active {
            background: green !important;
        }
        .logout-link {
            display: inline-block;
            float: right;
            background: #555;
            color: #fff;
            padding: 8px 15px;
            text-decoration: none;
            border-radius: 5px;
        }
    </style>
</head>
<body>
<div class="container">
    <h1>لوحة تحكم الأدمن</h1>
    <a class="logout-link" href="{{ url_for('admin_logout') }}">تسجيل خروج</a>
    <div class="section">
        <h2>توليد كود جديد</h2>
        <form method="POST">
            <label>مدة (ساعات):</label>
            <input type="number" name="duration" value="1" min="1">
            <button class="btn" name="generate_code" value="1">توليد</button>
        </form>
    </div>
    <div class="section">
        <h2>تفعيل/إيقاف الفاليديتور</h2>
<form method="POST">
    <p>
        Validator 1:
        <button class="switch-btn {% if validator1_active %}active{% endif %}"
                name="toggle_validator"
                value="validator1">
            {% if validator1_active %}مفعّل{% else %}معطّل{% endif %}
        </button>
        <input type="hidden" name="validator" value="validator1">
        <input type="hidden" name="status" value="{{ 'false' if validator1_active else 'true' }}">
    </p>
</form>

<form method="POST">
    <p>
        Validator 2:
        <button class="switch-btn {% if validator2_active %}active{% endif %}"
                name="toggle_validator"
                value="validator2">
            {% if validator2_active %}مفعّل{% else %}معطّل{% endif %}
        </button>
        <input type="hidden" name="validator" value="validator2">
        <input type="hidden" name="status" value="{{ 'false' if validator2_active else 'true' }}">
    </p>
</form>
    </div>
    <div class="section">
        <h2>الأكواد النشطة</h2>
        <table>
            <tr>
                <th>الكود</th>
                <th>ينتهي في</th>
                <th>مستخدم من IP</th>
            </tr>
            {% for c in active_codes %}
            <tr>
                <td>{{ c.code }}</td>
                <td>{{ c.expires_at }}</td>
                <td>{{ c.ip if c.ip else '' }}</td>
            </tr>
            {% endfor %}
        </table>
    </div>
    <form method="POST" action="{{ url_for('change_admin') }}">
            <input type="text" name="username" placeholder="اسم المستخدم الجديد" required>
            <input type="password" name="password" placeholder="كلمة المرور الجديدة" required>
            <button type="submit">تغيير</button>
        </form>
</div>
</body>
</html>
"""

@app.route("/change_admin", methods=["POST"])
def change_admin():
    new_username = request.form["username"]
    new_password = request.form["password"]
    admin_collection.update_one({"_id": "admin"}, {"$set": {"username": new_username, "password": new_password}})
    return redirect(url_for("admin_dashboard"))


