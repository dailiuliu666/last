async function qjson(url) {
    const response = await fetch(url);
    return await response.json();
}

async function qcall(url, options = {}) {
    const response = await fetch(url, options);
    return await response.json();
}

function val(id) {
    return document.getElementById(id)?.value?.trim() || '';
}

function factorBadge(type) {
    const text = String(type || '').toLowerCase();
    if (text.includes('technical') || text.includes('momentum') || text.includes('vol')) return 'blue';
    if (text.includes('fundamental')) return 'green';
    if (text.includes('money')) return 'yellow';
    if (text.includes('chip')) return 'cyan';
    return 'gray';
}

function fmtNumber(value, digits = 4) {
    const number = Number(value);
    return Number.isFinite(number) ? number.toFixed(digits) : '-';
}

function scoreCell(value) {
    const number = Number(value);
    if (!Number.isFinite(number)) return '-';
    const width = Math.max(6, Math.min(100, Math.abs(number) * 26));
    const color = number >= 0 ? '#1668f2' : '#f6b300';
    return `
        <span class="score-bar">
            <span class="score-track"><span class="score-fill" style="width:${width}%;background:${color}"></span></span>
            <span>${number.toFixed(3)}</span>
        </span>
    `;
}
