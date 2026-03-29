// UI Elements
const loginModal = document.getElementById('login-modal');
const chatIdInput = document.getElementById('chat-id-input');
const otpInput = document.getElementById('otp-input');
const authError = document.getElementById('auth-error');

const mainHeader = document.getElementById('main-header');
const dashboardContent = document.getElementById('dashboard-content');
const userNameDisplay = document.getElementById('user-name');
const adminLink = document.getElementById('admin-link');

const settingsModal = document.getElementById('settings-modal');
const userProxyInput = document.getElementById('user-proxy-input');
const reqOverlay = document.getElementById('requirements-overlay');
const neededList = document.getElementById('needed-list');

const stripeUrlInput = document.getElementById('stripe-url');
const cardsInput = document.getElementById('cards-input');
const startBtn = document.getElementById('start-btn');
const logOutput = document.getElementById('log-output');
const resultsOverview = document.getElementById('results-overview');
const successOverlay = document.getElementById('success-overlay');

let activeGate = 'checkout';
let activeMode = 'cards';
let stats = { total: 0, charged: 0, bypassed: 0, declined: 0 };
let currentChatId = '';

// --- INITIALIZATION ---

window.onload = async () => {
    try {
        const res = await fetch('/api/check-session');
        const data = await res.json();
        if (data.success) {
            currentChatId = data.chat_id;
            if (data.is_admin) adminLink.style.display = 'inline';
            if (data.proxy) userProxyInput.value = data.proxy;
            showDashboard();
            checkRequirements(); // Check if user joined channels
        }
    } catch (e) { }
};

async function checkRequirements() {
    try {
        const res = await fetch('/api/check-requirements');
        const data = await res.json();
        if (data.success && !data.all_joined) {
            neededList.innerHTML = data.needed.map(req => `
                <div class="req-item" style="margin-top:10px; background:var(--surface); padding:10px; border-radius:8px;">
                    <div style="font-size:13px; font-weight:600;">${req.name}</div>
                    <a href="${req.url}" target="_blank" style="font-size:11px; color:var(--primary);">JOIN NOW</a>
                </div>
            `).join('');
            reqOverlay.style.display = 'flex';
        } else {
            reqOverlay.style.display = 'none';
        }
    } catch (e) { }
}

document.getElementById('verify-req-btn').onclick = () => checkRequirements();

// --- AUTH FLOW ---

document.getElementById('send-otp-btn').onclick = async () => {
    const chatId = chatIdInput.value.trim();
    if (!chatId) return (authError.innerText = "Please enter your Chat ID");
    try {
        const res = await fetch('/api/send-otp', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ chat_id: chatId })
        });
        const data = await res.json();
        if (data.success) {
            currentChatId = chatId;
            document.getElementById('auth-phase-1').style.display = 'none';
            document.getElementById('auth-phase-2').style.display = 'block';
            authError.innerText = "";
        }
    } catch (e) { }
};

document.getElementById('verify-otp-btn').onclick = async () => {
    const code = otpInput.value.trim();
    try {
        const res = await fetch('/api/verify-otp', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ chat_id: currentChatId, code: code })
        });
        const data = await res.json();
        if (data.success) location.reload();
    } catch (e) { }
};

function showDashboard() {
    loginModal.style.display = 'none';
    mainHeader.style.display = 'flex';
    dashboardContent.style.display = 'block';
    userNameDisplay.innerText = `User ID: ${currentChatId}`;
}

// --- SETTINGS ---

document.getElementById('settings-btn').onclick = () => {
    settingsModal.style.display = 'flex';
};

document.getElementById('close-settings').onclick = () => {
    settingsModal.style.display = 'none';
};

document.getElementById('save-settings-btn').onclick = async () => {
    const proxy = userProxyInput.value.trim();
    try {
        await fetch('/api/user/proxy', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ proxy: proxy })
        });
        alert("Settings Saved!");
        settingsModal.style.display = 'none';
    } catch (e) { }
};

document.getElementById('logout-btn').onclick = async () => {
    if (confirm("Logout?")) {
        await fetch('/api/logout', { method: 'POST' });
        location.reload();
    }
};

adminLink.onclick = () => { window.location.href = '/admin'; };

// --- GATE & MODE SWITCHING ---

document.querySelectorAll('.gate-card').forEach(card => {
    card.onclick = () => {
        document.querySelectorAll('.gate-card').forEach(c => c.classList.remove('active'));
        card.classList.add('active');
        activeGate = card.dataset.gate;
    };
});

document.getElementById('mode-cards-tab').onclick = () => {
    activeMode = 'cards';
    document.getElementById('mode-cards-tab').classList.add('active');
    document.getElementById('mode-bin-tab').classList.remove('active');
    document.getElementById('input-cards-area').style.display = 'block';
    document.getElementById('input-bin-area').style.display = 'none';
};

document.getElementById('mode-bin-tab').onclick = () => {
    activeMode = 'bin';
    document.getElementById('mode-bin-tab').classList.add('active');
    document.getElementById('mode-cards-tab').classList.remove('active');
    document.getElementById('input-cards-area').style.display = 'none';
    document.getElementById('input-bin-area').style.display = 'block';
};

// --- HITTER LOGIC ---

startBtn.onclick = async () => {
    const url = stripeUrlInput.value.trim();
    let cards = [];

    if (activeMode === 'cards') {
        const text = cardsInput.value.trim();
        cards = text.split('\n').map(c => c.trim()).filter(c => c.length > 0);
    } else {
        const bin = document.getElementById('bin-input').value.trim();
        const amt = parseInt(document.getElementById('bin-amount').value) || 1;
        cards = generateCards(bin, amt);
    }
    
    if (!url || cards.length === 0) return alert("URL & Cards required!");
    
    resetStats();
    resultsOverview.style.display = 'block';
    startBtn.disabled = true;

    for (const card of cards) {
        stats.total++;
        updateStats();
        const startTime = performance.now();
        
        try {
            const res = await fetch('/api/hit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    url: url,
                    card: card,
                    gate: activeGate
                })
            });
            
            const data = await res.json();
            const elapsed = ((performance.now() - startTime) / 1000).toFixed(2);
            handleResult(card, data, elapsed);
            
            if (data.status === 'charged') {
                showSuccessNotification(data.message);
                break; 
            }
        } catch (e) {
            handleResult(card, { status: 'error', message: 'Request Failed' }, "0.00");
        }
    }
    startBtn.disabled = false;
};

function handleResult(card, data, time) {
    const status = (data.status || 'error').toLowerCase();
    if (status === 'charged') stats.charged++;
    else if (status === '3ds') stats.bypassed++;
    else stats.declined++;
    
    addResultCard(card, status, (data.message || 'Result'), time);
    updateStats();
}

function addResultCard(card, status, msg, time) {
    const item = document.createElement('div');
    item.className = 'log-item-card';
    const statusClass = (status === 'charged' ? 'charged' : (status === '3ds' ? 'bypassed' : 'dead'));
    
    item.innerHTML = `
        <div class="row-header">
            <div class="row-card-info">💳 ${card.split('|')[0]}</div>
            <div class="row-status-badge bg-${statusClass}">${status.toUpperCase()}</div>
        </div>
        <div class="status-msg text-${statusClass}">${msg}</div>
        <div class="row-time">${time}s</div>
    `;
    logOutput.prepend(item);
}

function showSuccessNotification(message) {
    document.getElementById('notif-message').innerText = message;
    successOverlay.classList.add('show');
    setTimeout(() => successOverlay.classList.remove('show'), 5000);
}

function generateCards(bin, count) {
    const cards = [];
    for (let i = 0; i < count; i++) {
        let card = bin; while (card.length < 16) card += Math.floor(Math.random() * 10);
        cards.push(`${card}|${String(Math.floor(Math.random() * 12) + 1).padStart(2, '0')}|${Math.floor(Math.random() * 5) + 25}|${Math.floor(Math.random() * 900) + 100}`);
    }
    return cards;
}

function resetStats() { stats = { total: 0, charged: 0, bypassed: 0, declined: 0 }; logOutput.innerHTML = ""; }
function updateStats() {
    document.getElementById('stat-total').innerText = `${stats.total} total`;
    document.getElementById('stat-charged').innerText = `${stats.charged} Charged`;
    document.getElementById('stat-bypassed').innerText = `${stats.bypassed} 3DS Bypassed`;
    document.getElementById('stat-declined').innerText = `${stats.declined} Declined`;
}
