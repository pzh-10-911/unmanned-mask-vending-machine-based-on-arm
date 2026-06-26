// script.js — 前端交互逻辑 (addEventListener version)
var API_BASE = window.location.origin;

var state = { state: 0, state_name: 'IDLE', balance: 0, selected_channel: null, channels: [] };
var selectedProduct = null;
var resultTimerId = null;
var confirming = false;

/********************* 初始化 *********************/
window.addEventListener('DOMContentLoaded', function() {
    console.log('[INIT] v3 addEventListener mode');

    // 绑定按钮事件
    document.getElementById('btn-coin').addEventListener('click', onCoinClick);
    document.getElementById('btn-cancel').addEventListener('click', onCancelClick);
    document.getElementById('btn-confirm-yes').addEventListener('click', onConfirmClick);
    document.getElementById('btn-confirm-no').addEventListener('click', closeConfirmModal);
    document.getElementById('modal-overlay').addEventListener('click', closeConfirmModal);

    fetchStatus();
    setInterval(fetchStatus, 1000);
});

/********************* API *********************/
function fetchStatus() {
    fetch(API_BASE + '/api/status?_=' + Date.now())
        .then(function(r) { return r.json(); })
        .then(function(data) { state = data; renderUI(); })
        .catch(function(e) { console.warn('[fetchStatus]', e.message); });
}

function onCoinClick() {
    if (confirming) return;
    fetch(API_BASE + '/api/coin', { method: 'POST' })
        .then(function(r) { return r.json(); })
        .then(function(data) { state.balance = data.balance; renderUI(); })
        .catch(function(e) { alert('投币失败: ' + e.message); });
}

function onBuyClick(channelId) {
    if (confirming) return;
    if (state.state !== 0) { alert('当前状态无法操作'); return; }
    console.log('[onBuyClick] channel=' + channelId);
    fetch(API_BASE + '/api/select/' + channelId, { method: 'POST' })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            console.log('[onBuyClick] result:', data);
            if (data.success) {
                selectedProduct = data;
                state.selected_channel = data.channel;
                document.getElementById('confirm-name').textContent = data.name;
                document.getElementById('confirm-price').textContent = data.price.toFixed(1);
                document.getElementById('confirm-balance').textContent = state.balance.toFixed(1);
                document.getElementById('confirm-after-balance').textContent = (state.balance - data.price).toFixed(1);
                showPage('page-confirm');
            } else {
                alert(data.msg);
            }
        })
        .catch(function(e) { alert('选择商品失败: ' + e.message); });
}

function onConfirmClick(e) {
    e.stopPropagation();
    e.preventDefault();
    if (confirming) { console.log('[onConfirmClick] already confirming'); return; }
    confirming = true;
    console.log('[onConfirmClick] sending...');
    fetch(API_BASE + '/api/confirm', { method: 'POST' })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            console.log('[onConfirmClick] result:', data);
            if (data.success) {
                showPage('page-result');
                document.getElementById('result-icon').textContent = '请取货';
                document.getElementById('result-message').textContent = '购买成功！请取走口罩';
                document.getElementById('progress-wrapper').style.display = 'flex';
                var bar = document.getElementById('progress-bar');
                bar.classList.remove('progress-bar');
                void bar.offsetWidth;
                bar.classList.add('progress-bar');
                if (selectedProduct) {
                    state.balance -= selectedProduct.price;
                    var ch = state.channels.find(function(c) { return c.id === selectedProduct.channel; });
                    if (ch) { ch.stock -= 1; if (ch.stock <= 0) ch.available = false; }
                }
                selectedProduct = null;
                startResultTimer();
            } else {
                showPage('page-result');
                document.getElementById('result-icon').textContent = '失败';
                document.getElementById('result-message').textContent = data.msg || '交易失败';
                document.getElementById('progress-wrapper').style.display = 'none';
                startResultTimer();
            }
        })
        .catch(function(e) { alert('确认购买失败: ' + e.message); })
        .finally(function() { confirming = false; });
}

function onCancelClick() {
    if (confirming) return;
    fetch(API_BASE + '/api/cancel', { method: 'POST' })
        .then(function() {
            state.balance = 0; state.selected_channel = null;
            showPage('page-main'); renderUI();
        })
        .catch(function() {
            state.balance = 0; state.selected_channel = null;
            showPage('page-main'); renderUI();
        });
}

/********************* UI *********************/
function renderUI() {
    document.getElementById('balance').textContent = state.balance;
    var cancelBtn = document.getElementById('btn-cancel');
    cancelBtn.style.display = (state.balance > 0 && state.state === 0) ? 'block' : 'none';

    var container = document.getElementById('product-list');
    container.innerHTML = '';
    state.channels.forEach(function(ch) {
        var canBuy = ch.available && state.balance >= ch.price && state.state === 0;
        var btnText = '购买';
        if (!ch.available) btnText = '缺货';
        else if (state.balance < ch.price) btnText = '余额不足';

        var card = document.createElement('div');
        card.className = 'card';
        card.innerHTML = '<div class="product-info">' +
            '<span class="product-name">' + ch.name + '</span>' +
            '<span class="product-price">¥' + ch.price.toFixed(1) + '</span>' +
            '<span class="product-stock">库存: ' + ch.stock + '</span>' +
            '</div>';

        var btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'product-btn';
        btn.textContent = btnText;
        if (!canBuy) btn.disabled = true;
        (function(cid) {
            btn.addEventListener('click', function() { onBuyClick(cid); });
        })(ch.id);
        card.appendChild(btn);
        container.appendChild(card);
    });
}

function showPage(pageId) {
    console.log('[showPage] ' + pageId);
    ['page-main', 'page-confirm', 'page-result'].forEach(function(id) {
        document.getElementById(id).style.display = (id === pageId) ? 'block' : 'none';
    });
    if (pageId !== 'page-result' && resultTimerId) {
        clearTimeout(resultTimerId);
        resultTimerId = null;
    }
}

function closeConfirmModal(e) {
    if (e) e.stopPropagation();
    if (confirming) { console.log('[closeConfirmModal] confirming, skip'); return; }
    console.log('[closeConfirmModal]');
    fetch(API_BASE + '/api/cancel_select', { method: 'POST' }).catch(function(){});
    showPage('page-main');
    selectedProduct = null;
}

function startResultTimer() {
    if (resultTimerId) clearTimeout(resultTimerId);
    var countdown = 30;
    var timerEl = document.getElementById('result-timer');
    timerEl.textContent = countdown + ' 秒后返回';
    resultTimerId = setInterval(function() {
        countdown--;
        if (countdown <= 0) {
            clearInterval(resultTimerId);
            resultTimerId = null;
            showPage('page-main');
            renderUI();
        } else {
            timerEl.textContent = countdown + ' 秒后返回';
        }
    }, 1000);
}
