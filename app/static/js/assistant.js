class FinanceChatApp {
    constructor() {
        this.chatMessages = document.getElementById('chatMessages');
        this.userInput = document.getElementById('userInput');
        this.sendButton = document.getElementById('sendButton');
        this.isProcessing = false;
        this.thinkingStartTime = null;
        this.init();
    }

    init() {
        this.sendButton.addEventListener('click', () => this.handleSend());
        this.userInput.addEventListener('keydown', (event) => {
            if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
                event.preventDefault();
                this.handleSend();
            }
        });
        this.userInput.addEventListener('input', () => this.autoResize());
        document.querySelectorAll('.quick-btn').forEach((button) => {
            button.addEventListener('click', () => {
                const query = button.dataset.query;
                if (query && !this.isProcessing) {
                    this.userInput.value = query;
                    this.handleSend();
                }
            });
        });
    }

    autoResize() {
        this.userInput.style.height = 'auto';
        this.userInput.style.height = Math.min(this.userInput.scrollHeight, 120) + 'px';
    }

    scrollToBottom() {
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }

    async handleSend() {
        const message = this.userInput.value.trim();
        if (!message || this.isProcessing) return;

        this.isProcessing = true;
        this.sendButton.disabled = true;
        this.addUserMessage(message);
        this.userInput.value = '';
        this.userInput.style.height = 'auto';

        const botMsg = this.createBotMessage();
        this.thinkingStartTime = Date.now();

        try {
            await this.streamResponse(message, botMsg);
        } catch (error) {
            this.addError(botMsg, '请求失败：' + error.message);
        } finally {
            this.isProcessing = false;
            this.sendButton.disabled = false;
            this.userInput.focus();
        }
    }

    addUserMessage(text) {
        const div = document.createElement('div');
        div.className = 'msg msg-user';
        div.innerHTML = `<div class="msg-bubble">${this.escapeHtml(text)}</div>`;
        this.chatMessages.appendChild(div);
        this.scrollToBottom();
    }

    createBotMessage() {
        const div = document.createElement('div');
        div.className = 'msg msg-bot';
        div.innerHTML = `
            <div class="msg-body">
                <div class="thinking-section">
                    <div class="thinking-header">
                        <div class="thinking-icon">AI</div>
                        <span class="thinking-text">正在处理...</span>
                    </div>
                    <div class="thinking-steps"></div>
                </div>
                <div class="msg-content" style="display:none"></div>
            </div>
        `;
        this.chatMessages.appendChild(div);
        this.scrollToBottom();
        return div;
    }

    addThinkingStep(botMsg, label, details) {
        const steps = botMsg.querySelector('.thinking-steps');
        if (!steps) return;
        steps.querySelectorAll('.thinking-step.in-progress').forEach((element) => {
            element.classList.remove('in-progress');
            element.querySelector('.step-check').textContent = '✓';
        });

        const step = document.createElement('div');
        step.className = 'thinking-step in-progress';
        step.innerHTML = `
            <span class="step-check">●</span>
            <span class="step-label">${this.escapeHtml(label)}</span>
        `;
        steps.appendChild(step);

        if (details) {
            const detail = document.createElement('div');
            detail.className = 'step-details';
            detail.innerHTML = `<div class="step-detail-item">${this.escapeHtml(details)}</div>`;
            steps.appendChild(detail);
        }
        this.scrollToBottom();
    }

    finishThinking(botMsg) {
        const section = botMsg.querySelector('.thinking-section');
        if (!section) return;
        section.querySelectorAll('.thinking-step.in-progress').forEach((element) => {
            element.classList.remove('in-progress');
            element.querySelector('.step-check').textContent = '✓';
        });
        const elapsed = ((Date.now() - this.thinkingStartTime) / 1000).toFixed(1);
        section.querySelector('.thinking-text').textContent = `已完成，用时 ${elapsed} 秒`;
    }

    addError(botMsg, text) {
        const thinking = botMsg.querySelector('.thinking-section');
        if (thinking) thinking.style.display = 'none';
        const contentDiv = botMsg.querySelector('.msg-content');
        contentDiv.style.display = 'block';
        contentDiv.innerHTML = `<div class="msg-error">${this.escapeHtml(text)}</div>`;
        this.scrollToBottom();
    }

    streamResponse(message, botMsg) {
        return new Promise((resolve) => {
            const source = new EventSource(`/api/assistant/chat/stream?message=${encodeURIComponent(message)}`);
            let fullText = '';
            let hasContent = false;
            let handledError = false;
            let timeoutTimer = setTimeout(() => {
                source.close();
                if (!hasContent) this.addError(botMsg, '请求超时，请稍后重试。');
                resolve();
            }, 60000);

            const resetTimeout = () => {
                clearTimeout(timeoutTimer);
                timeoutTimer = setTimeout(() => {
                    source.close();
                    resolve();
                }, 60000);
            };

            source.addEventListener('tool_call', (event) => {
                resetTimeout();
                try {
                    const data = JSON.parse(event.data);
                    this.addThinkingStep(botMsg, this.getToolLabel(data.name), this.getToolDetail(data.args));
                } catch (error) {
                    console.error('解析工具调用失败:', error);
                }
            });

            source.addEventListener('message', (event) => {
                resetTimeout();
                if (!hasContent) {
                    hasContent = true;
                    this.finishThinking(botMsg);
                    botMsg.querySelector('.msg-content').style.display = 'block';
                }
                fullText += event.data;
                this.renderContent(botMsg, fullText);
            });

            source.addEventListener('ping', (event) => {
                resetTimeout();
                try {
                    const data = JSON.parse(event.data);
                    this.addThinkingStep(botMsg, '仍在处理', data.message || '数据源或模型仍在响应中');
                } catch {
                    this.addThinkingStep(botMsg, '仍在处理', '数据源或模型仍在响应中');
                }
            });

            source.addEventListener('done', () => {
                clearTimeout(timeoutTimer);
                source.close();
                if (!hasContent) {
                    this.finishThinking(botMsg);
                    botMsg.querySelector('.msg-content').style.display = 'block';
                }
                if (fullText) this.renderContent(botMsg, fullText);
                resolve();
            });

            source.addEventListener('error', (event) => {
                clearTimeout(timeoutTimer);
                handledError = true;
                if (event.data) this.addError(botMsg, event.data);
                source.close();
                resolve();
            });

            source.onerror = () => {
                clearTimeout(timeoutTimer);
                if (!hasContent && !handledError) this.addError(botMsg, '连接失败，请检查主平台服务是否运行。');
                source.close();
                resolve();
            };
        });
    }

    getToolLabel(name) {
        const labels = {
            get_stock_info: '正在查询实时行情和基础资料',
            get_stock_history: '正在获取历史日线行情',
            get_financial_statement: '正在读取核心财务指标',
            get_stock_news: '正在检索个股新闻',
            get_recommendations: '正在查询盈利预测和研报摘要',
            compare_stocks: '正在进行多股横向对比',
            search_financial_news: '正在搜索财经资讯',
            think: '正在整理中间结论',
        };
        return labels[name] || `调用 ${name}`;
    }

    getToolDetail(args) {
        if (!args) return null;
        if (args.stock_code) return `股票代码：${args.stock_code}`;
        if (args.stock_codes) return `对比：${args.stock_codes}`;
        if (args.query) return `搜索：${args.query}`;
        return null;
    }

    renderContent(botMsg, text) {
        const contentDiv = botMsg.querySelector('.msg-content');
        contentDiv.innerHTML = this.markdownToHtml(text);
        this.scrollToBottom();
    }

    markdownToHtml(text) {
        let html = this.escapeHtml(text || '');
        html = this.renderAssistantJsonBlocks(html);
        html = html.replace(/^### (.*)$/gm, '<h3>$1</h3>');
        html = html.replace(/^## (.*)$/gm, '<h2>$1</h2>');
        html = html.replace(/^# (.*)$/gm, '<h1>$1</h1>');
        html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
        html = html.replace(/`(.+?)`/g, '<code>$1</code>');
        html = html.replace(/\n\n+/g, '</p><p>');
        html = html.replace(/\n/g, '<br>');
        return `<p>${html}</p>`;
    }

    renderAssistantJsonBlocks(html) {
        return html.replace(/```text<br>([\s\S]*?)<br>```/g, (match, body) => {
            const decoded = this.decodeHtml(body.replace(/<br>/g, '\n')).trim();
            const card = this.tryRenderJsonCard(decoded);
            return card || `<pre class="assistant-data-card"><code>${this.escapeHtml(decoded)}</code></pre>`;
        });
    }

    tryRenderJsonCard(text) {
        let data;
        try {
            data = JSON.parse(text);
        } catch {
            return null;
        }
        if (Array.isArray(data)) {
            return this.renderArrayCard('查询结果', data);
        }
        if (data && typeof data === 'object') {
            if (data['汇总'] && data['近期交易数据']) {
                return this.renderObjectCard('走势汇总', data['汇总']) + this.renderArrayCard('近期交易数据', data['近期交易数据']);
            }
            return this.renderObjectCard(data['股票名称'] || data['股票代码'] || '数据结果', data);
        }
        return null;
    }

    renderObjectCard(title, object) {
        const entries = Object.entries(object || {}).filter(([, value]) => {
            return value == null || typeof value !== 'object';
        });
        if (!entries.length) return '';
        return `
            <div class="assistant-data-card">
                <div class="assistant-data-title">${this.escapeHtml(String(title))}</div>
                <div class="assistant-data-grid">
                    ${entries.map(([key, value]) => `
                        <div class="assistant-data-item">
                            <span>${this.escapeHtml(String(key))}</span>
                            <strong>${this.escapeHtml(String(value ?? '-'))}</strong>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    renderArrayCard(title, rows) {
        const safeRows = rows.slice(0, 8).filter((item) => item && typeof item === 'object');
        if (!safeRows.length) return '';
        const keys = Array.from(new Set(safeRows.flatMap((row) => Object.keys(row)))).slice(0, 6);
        return `
            <div class="assistant-data-card">
                <div class="assistant-data-title">${this.escapeHtml(title)}</div>
                <div class="table-wrap">
                    <table>
                        <thead><tr>${keys.map((key) => `<th>${this.escapeHtml(key)}</th>`).join('')}</tr></thead>
                        <tbody>
                            ${safeRows.map((row) => `
                                <tr>${keys.map((key) => `<td>${this.escapeHtml(String(row[key] ?? '-'))}</td>`).join('')}</tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    }

    decodeHtml(html) {
        const textarea = document.createElement('textarea');
        textarea.innerHTML = html;
        return textarea.value;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.financeChatApp = new FinanceChatApp();
});
