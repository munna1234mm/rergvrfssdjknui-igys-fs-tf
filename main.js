// UI Elements
const loginModal = document.getElementById('login-modal');
const authPhase1 = document.getElementById('auth-phase-1');
const authPhase2 = document.getElementById('auth-phase-2');
const chatIdInput = document.getElementById('chat-id-input');
const otpInput = document.getElementById('otp-input');
const authError = document.getElementById('auth-error');

const mainHeader = document.getElementById('main-header');
const dashboardContent = document.getElementById('dashboard-content');
const logoutBtn = document.getElementById('logout-btn');

const stripeUrlInput = document.getElementById('stripe-url');
const cardsInput = document.getElementById('cards-input');
const startBtn = document.getElementById('start-btn');
const browserModeToggle = document.getElementById('browser-mode-toggle');
const logOutput = document.getElementById('log-output');
const resultsOverview = document.getElementById('results-overview');

let activeGate = 'checkout';
let stats = { total: 0, charged: 0, bypassed: 0, declined: 0 };
let currentChatId = '';

// --- AUTH FLOW ---

document.getElementById('send-otp-btn').onclick = async () => {
    const chatId = chatIdInput.value.trim();
    if (!chatId) return (authError.innerText = "Please enter your Chat ID");
    
    authError.innerText = "Sending code...";
    try {
        const res = await fetch('/api/send-otp', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ chat_id: chatId })
        });
        const data = await res.json();
        if (data.success) {
            currentChatId = chatId;
            authPhase1.style.display = 'none';
            authPhase2.style.display = 'block';
            authError.innerText = "";
        } else {
            authError.innerText = data.message;
        }
    } catch (e) {
        authError.innerText = "Error connecting to server";
    }
};

document.getElementById('verify-otp-btn').onclick = async () => {
    const code = otpInput.value.trim();
    if (code.length < 6) return (authError.innerText = "Invalid code format");

    try {
        const res = await fetch('/api/verify-otp', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ chat_id: currentChatId, code: code })
        });
        const data = await res.json();
        if (data.success) {
            showDashboard();
        } else {
            authError.innerText = "Invalid verification code";
        }
    } catch (e) {
        authError.innerText = "Verification failed";
    }
};

document.getElementById('back-to-phase-1').onclick = () => {
    authPhase2.style.display = 'none';
    authPhase1.style.display = 'block';
};

logoutBtn.onclick = () => {
    // Basic logout
    location.reload();
};

function showDashboard() {
    loginModal.style.display = 'none';
    mainHeader.style.display = 'flex';
    dashboardContent.style.display = 'block';
}

// --- DASHBOARD LOGIC ---

document.querySelectorAll('.tab').forEach(tab => {
    tab.onclick = () => {
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        activeGate = tab.dataset.gate;
    };
});

startBtn.onclick = async () => {
    const url = stripeUrlInput.value.trim();
    const cardsText = cardsInput.value.trim();
    const useBrowser = browserModeToggle.checked;
    
    if (!url || !cardsText) return alert("Please provide URL and Cards");
    
    const cards = cardsText.split('\n').map(c => c.trim()).filter(c => c.length > 0);
    resetStats();
    resultsOverview.style.display = 'block';
    
    startBtn.disabled = true;
    startBtn.innerText = "PROCESSING...";

    for (const card of cards) {
        stats.total++;
        updateStats();
        
        try {
            const res = await fetch('/api/hit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    url: url,
                    card: card,
                    gate: activeGate,
                    use_browser: useBrowser
                })
            });
            
            const data = await res.json();
            handleResult(card, data);
            
            if (data.status === 'charged') {
                if (useBrowser) break; // User usually stops after success in browser mode
            }
        } catch (e) {
            handleResult(card, { status: 'error', message: 'Request Failed' });
        }
    }
    
    startBtn.disabled = false;
    startBtn.innerText = "START HITTING";
};

function handleResult(card, data) {
    const status = (data.status || 'error').toLowerCase();
    const msg = data.message || 'Unknown result';
    
    if (status === 'charged' || status === 'approved') stats.charged++;
    else if (status === '3ds' || msg.toLowerCase().includes('3d')) stats.bypassed++;
    else stats.declined++;
    
    addLogEntry(card, status, msg);
    updateStats();
}

function addLogEntry(card, status, msg) {
    const item = document.createElement('div');
    item.className = 'log-item';
    
    let color = 'white';
    if (status === 'charged') color = '#34c759';
    else if (status === '3ds') color = '#ff9500';
    else if (status === 'dead' || status === 'error') color = '#ff3b30';

    item.innerHTML = `
        <div>
            <div class="card-number">${maskCard(card)}</div>
            <div class="status-text" style="color: ${color}">${msg}</div>
        </div>
        <div class="badge">${status.toUpperCase()}</div>
    `;
    logOutput.prepend(item);
}

function resetStats() {
    stats = { total: 0, charged: 0, bypassed: 0, declined: 0 };
    logOutput.innerHTML = "";
}

function updateStats() {
    document.getElementById('stat-total').innerText = `${stats.total} total`;
    document.getElementById('stat-charged').innerText = `${stats.charged} Charged`;
    document.getElementById('stat-3ds').innerText = `${stats.bypassed} 3DS Bypassed`;
    document.getElementById('stat-declined').innerText = `${stats.declined} Declined`;
}

function maskCard(card) {
    const p = card.split('|')[0];
    return p.length > 6 ? `******${p.substring(6)}` : p;
}
