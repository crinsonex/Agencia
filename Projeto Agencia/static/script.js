(function () {
    'use strict';

    var COLORS = ['#4f46e5','#06b6d4','#f59e0b','#10b981','#f97316','#ec4899','#6366f1','#14b8a6'];
    var barChart = null, donutChart = null, lineChart = null, salesBarChart = null, sellersStackedChart = null;
    var currentMonth = null;
    var currentTab = 'mensal';

    // ---- Utilities ----
    function fmt(v) {
        return 'R$ ' + Number(v).toLocaleString('pt-BR', {minimumFractionDigits:2, maximumFractionDigits:2});
    }

    function fmtShort(v) {
        if (v >= 1000000) return (v/1000000).toFixed(1) + 'M';
        if (v >= 1000) return (v/1000).toFixed(1) + 'k';
        return v.toFixed(0);
    }

    // ---- Sidebar ----
    function buildSidebar() {
        var menu = document.getElementById('sidebar-menu');
        menu.innerHTML = '';
        var keys = Object.keys(DATA);
        if (!keys.length) {
            document.getElementById('month-count').textContent = 'Nenhum mes';
            return;
        }
        keys.forEach(function(key, i) {
            var li = document.createElement('li');
            li.textContent = DATA[key].meta.display;
            li.dataset.month = key;
            if (i === 0 && !currentMonth) li.classList.add('active');
            if (key === currentMonth) li.classList.add('active');
            li.onclick = function() { selectMonth(key); };
            menu.appendChild(li);
        });
        document.getElementById('month-count').textContent = keys.length + ' mes' + (keys.length > 1 ? 'es' : '');
    }

    // ---- Month selection ----
    function selectMonth(key) {
        currentMonth = key;
        var d = DATA[key];
        if (!d) return;
        var k = d.kpi;

        document.querySelectorAll('.sidebar-menu li, .sidebar-menu .menu-item-with-delete').forEach(function(el) {
            el.classList.toggle('active', el.dataset.month === key);
        });

        document.getElementById('month-title').textContent = k.display || key;
        var tot = k.pagos + k.pendentes;
        var conv = tot > 0 ? Math.round(k.pagos / tot * 100) + '% pago' : '\u2014';
        document.getElementById('month-subtitle').textContent =
            'Faturamento, comissoes e resultado \u2014 ' + conv + ' (' + tot + ' vendas)';

        // KPI cards
        var grid = document.getElementById('kpi-grid');
        grid.innerHTML = '';
        [
            {l:'Faturamento Bruto', v:fmt(k.total)},
            {l:'Total Taxas', v:fmt(k.taxas)},
            {l:'Liquido s/ Taxas', v:fmt(k.liquido)},
            {l:'Total Comissoes', v:fmt(k.comissoes)},
            {l:'Vendas Pagas', v:k.pagos + ' de ' + tot},
            {l:'Vendas Pendentes', v:k.pendentes}
        ].forEach(function(item) {
            var div = document.createElement('div');
            div.className = 'kpi-card';
            div.innerHTML = '<div class="label">' + item.l + '</div><div class="value">' + item.v + '</div>';
            grid.appendChild(div);
        });

        // Seller cards
        var sellers = document.getElementById('seller-panels');
        sellers.innerHTML = '';
        var sellerKeys = Object.keys(k.vendedores);
        if (sellerKeys.length) {
            var panel = document.createElement('div');
            panel.className = 'panel';
            panel.innerHTML = '<div class="panel-header"><h3>Por Vendedor</h3></div>';
            var sgrid = document.createElement('div');
            sgrid.className = 'seller-grid';
            sellerKeys.forEach(function(name) {
                var s = k.vendedores[name];
                var initials = name.split(' ').map(function(w){return w[0];}).join('').substring(0,2).toUpperCase();
                var card = document.createElement('div');
                card.className = 'seller-card';
                card.innerHTML =
                    '<div class="avatar">' + initials + '</div>' +
                    '<div class="info">' +
                        '<div class="name">' + name + '</div>' +
                        '<div class="meta">' + s.count + ' vendas | ' + s.pagos + ' pagas | ' + s.pendentes + ' pendentes</div>' +
                    '</div>' +
                    '<div class="seller-values">' +
                        '<div class="sv-total">' + fmt(s.total) + '</div>' +
                        '<div class="sv-liq">liquido: ' + fmt(s.liquido) + '</div>' +
                        '<div class="sv-com">comissao: ' + fmt(s.comissao) + '</div>' +
                    '</div>';
                sgrid.appendChild(card);
            });
            panel.appendChild(sgrid);
            sellers.appendChild(panel);
        }

        // Bar chart - sellers
        if (barChart) barChart.destroy();
        barChart = new Chart(document.getElementById('chart-bar'), {
            type: 'bar',
            data: {
                labels: sellerKeys,
                datasets: [{
                    data: sellerKeys.map(function(n){ return k.vendedores[n].total; }),
                    backgroundColor: COLORS.slice(0, sellerKeys.length),
                    borderRadius: 6,
                    barThickness: 40,
                }]
            },
            options: {
                responsive: true,
                plugins: { legend: { display: false } },
                scales: {
                    y: { beginAtZero: true, ticks: { callback: function(v){ return fmt(v); } } }
                }
            }
        });

        // Donut - products
        var pLabels = Object.keys(k.produtos);
        if (donutChart) donutChart.destroy();
        donutChart = new Chart(document.getElementById('chart-donut'), {
            type: 'doughnut',
            data: {
                labels: pLabels,
                datasets: [{
                    data: pLabels.map(function(n){ return k.produtos[n]; }),
                    backgroundColor: COLORS.slice(0, pLabels.length),
                    borderWidth: 0,
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { position: 'bottom', labels: { padding: 12, usePointStyle: true, font: {size: 11} } }
                }
            }
        });

        // Tx table
        var tbody = document.getElementById('tx-body');
        tbody.innerHTML = '';
        d.transactions.forEach(function(t) {
            var tr = document.createElement('tr');
            var stClass = t.status && t.status.toUpperCase().indexOf('PAGO') !== -1 ? 'PAGO' :
                          (t.status && t.status.toUpperCase().indexOf('PENDENTE') !== -1 ? 'PENDENTE' : 'VAZIO');
            var stText = t.status || '\u2014';
            tr.innerHTML =
                '<td>' + (t.id||'') + '</td>' +
                '<td>' + (t.nome||'') + '</td>' +
                '<td>' + (t.produto||'') + '</td>' +
                '<td><span class="badge ' + stClass + '">' + stText + '</span></td>' +
                '<td class="num">' + fmt(t.total||0) + '</td>' +
                '<td class="num">' + fmt(t.taxa||0) + '</td>' +
                '<td class="num">' + fmt(t.liquido||0) + '</td>' +
                '<td class="num">' + fmt(t.comissao||0) + '</td>' +
                '<td>' + (t.obs||'') + '</td>';
            tbody.appendChild(tr);
        });

        // Summary
        var sumList = document.getElementById('summary-list');
        sumList.innerHTML = '';
        if (d.summary && d.summary.length) {
            d.summary.forEach(function(line) {
                var li = document.createElement('li');
                li.textContent = line;
                sumList.appendChild(li);
            });
        }
    }

    // ---- Annual View ----
    function loadAnnual() {
        fetch('/api/annual')
            .then(function(r){ return r.json(); })
            .then(function(annual) {
                renderAnnual(annual);
            });
    }

    function renderAnnual(annual) {
        var months = annual.months;
        if (!months.length) {
            document.getElementById('kpi-anual-grid').innerHTML = '<p style="padding:20px">Nenhum mes disponivel</p>';
            return;
        }

        // Anual KPIs
        var grandTotal = 0, grandTaxas = 0, grandLiquido = 0, grandComissoes = 0, grandPagos = 0, grandPendientes = 0;
        months.forEach(function(m) {
            grandTotal += m.total; grandTaxas += m.taxas; grandLiquido += m.liquido;
            grandComissoes += m.comissoes; grandPagos += m.pagos; grandPendientes += m.pendentes;
        });

        var grid = document.getElementById('kpi-anual-grid');
        grid.innerHTML = '';
        [
            {l:'Faturamento Anual', v:fmt(grandTotal)},
            {l:'Taxas Anual', v:fmt(grandTaxas)},
            {l:'Liquido Anual', v:fmt(grandLiquido)},
            {l:'Comissoes Anual', v:fmt(grandComissoes)},
            {l:'Total Vendas', v:grandPagos + ' pagas / ' + grandPendientes + ' pendentes'},
            {l:'Meses', v:months.length}
        ].forEach(function(item) {
            var div = document.createElement('div');
            div.className = 'kpi-card';
            div.innerHTML = '<div class="label">' + item.l + '</div><div class="value">' + item.v + '</div>';
            grid.appendChild(div);
        });

        // Line chart - evolution
        if (lineChart) lineChart.destroy();
        lineChart = new Chart(document.getElementById('chart-line'), {
            type: 'line',
            data: {
                labels: months.map(function(m){ return m.display; }),
                datasets: [
                    {
                        label: 'Faturamento',
                        data: months.map(function(m){ return m.total; }),
                        borderColor: '#4f46e5',
                        backgroundColor: 'rgba(79,70,229,0.08)',
                        fill: true, tension: 0.3, pointRadius: 5, pointHoverRadius: 7,
                    },
                    {
                        label: 'Liquido s/ Taxas',
                        data: months.map(function(m){ return m.liquido; }),
                        borderColor: '#10b981',
                        backgroundColor: 'rgba(16,185,129,0.08)',
                        fill: true, tension: 0.3, pointRadius: 5, pointHoverRadius: 7,
                    },
                    {
                        label: 'Taxas',
                        data: months.map(function(m){ return m.taxas; }),
                        borderColor: '#f59e0b',
                        backgroundColor: 'rgba(245,158,11,0.06)',
                        fill: true, tension: 0.3, pointRadius: 4, pointHoverRadius: 6,
                    }
                ]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { position: 'top', labels: { padding: 16, usePointStyle: true } },
                    tooltip: {
                        callbacks: {
                            label: function(ctx) {
                                return ctx.dataset.label + ': ' + fmt(ctx.parsed.y);
                            }
                        }
                    }
                },
                scales: {
                    y: { beginAtZero: true, ticks: { callback: function(v){ return fmt(v); } } }
                }
            }
        });

        // Sales per month bar chart
        if (salesBarChart) salesBarChart.destroy();
        salesBarChart = new Chart(document.getElementById('chart-sales-bar'), {
            type: 'bar',
            data: {
                labels: months.map(function(m){ return m.display; }),
                datasets: [
                    {
                        label: 'Pagas',
                        data: months.map(function(m){ return m.pagos; }),
                        backgroundColor: '#16a34a',
                        borderRadius: 4, barPercentage: 0.6,
                    },
                    {
                        label: 'Pendentes',
                        data: months.map(function(m){ return m.pendentes; }),
                        backgroundColor: '#f59e0b',
                        borderRadius: 4, barPercentage: 0.6,
                    }
                ]
            },
            options: {
                responsive: true,
                plugins: { legend: { position: 'top', labels: { usePointStyle: true } } },
                scales: { x: { stacked: true }, y: { stacked: true, beginAtZero: true } }
            }
        });

        // Sellers stacked per month
        var sellerNames = Object.keys(annual.sellers);
        if (sellersStackedChart) sellersStackedChart.destroy();
        sellersStackedChart = new Chart(document.getElementById('chart-sellers-stacked'), {
            type: 'bar',
            data: {
                labels: months.map(function(m){ return m.display; }),
                datasets: sellerNames.map(function(name, i) {
                    return {
                        label: name,
                        data: months.map(function(m) {
                            return (annual.sellers[name] && annual.sellers[name][m.month]) || 0;
                        }),
                        backgroundColor: COLORS[i % COLORS.length],
                        borderRadius: 2,
                    };
                })
            },
            options: {
                responsive: true,
                scales: {
                    x: { stacked: true },
                    y: { stacked: true, beginAtZero: true, ticks: { callback: function(v){ return fmt(v); } } }
                },
                plugins: {
                    legend: { position: 'bottom', labels: { usePointStyle: true, font: {size: 11}, padding: 10 } }
                }
            }
        });

        // Annual summary table
        var tbody = document.getElementById('anual-tbody');
        tbody.innerHTML = '';
        months.forEach(function(m) {
            var tr = document.createElement('tr');
            tr.innerHTML =
                '<td>' + m.display + '</td>' +
                '<td class="num">' + fmt(m.total) + '</td>' +
                '<td class="num">' + fmt(m.taxas) + '</td>' +
                '<td class="num">' + fmt(m.liquido) + '</td>' +
                '<td class="num">' + fmt(m.comissoes) + '</td>' +
                '<td class="num">' + m.pagos + '</td>' +
                '<td class="num">' + m.pendentes + '</td>';
            tbody.appendChild(tr);
        });
        // Total row
        var tr = document.createElement('tr');
        tr.style.fontWeight = '700';
        tr.innerHTML =
            '<td>TOTAL</td>' +
            '<td class="num">' + fmt(grandTotal) + '</td>' +
            '<td class="num">' + fmt(grandTaxas) + '</td>' +
            '<td class="num">' + fmt(grandLiquido) + '</td>' +
            '<td class="num">' + fmt(grandComissoes) + '</td>' +
            '<td class="num">' + grandPagos + '</td>' +
            '<td class="num">' + grandPendientes + '</td>';
        tbody.appendChild(tr);
    }

    // ---- Tab switching ----
    window.switchTab = function(tab) {
        currentTab = tab;
        document.querySelectorAll('.tab').forEach(function(el) {
            el.classList.toggle('active', el.dataset.tab === tab);
        });
        document.getElementById('view-mensal').classList.toggle('hidden', tab !== 'mensal');
        document.getElementById('view-anual').classList.toggle('hidden', tab !== 'anual');

        var title = document.getElementById('month-title');
        var subtitle = document.getElementById('month-subtitle');

        if (tab === 'mensal') {
            title.textContent = DATA && currentMonth ? (DATA[currentMonth].meta.display || '-') : '-';
        } else {
            title.textContent = 'Visao Anual';
            subtitle.textContent = 'Evolucao dos resultados ao longo dos meses';
            loadAnnual();
        }
    };

    // ---- Upload handling ----
    function setupUpload() {
        var zone = document.getElementById('upload-zone');
        var input = document.getElementById('file-input');

        zone.addEventListener('click', function() { input.click(); });

        zone.addEventListener('dragover', function(e) {
            e.preventDefault();
            zone.classList.add('dragover');
        });
        zone.addEventListener('dragleave', function() {
            zone.classList.remove('dragover');
        });
        zone.addEventListener('drop', function(e) {
            e.preventDefault();
            zone.classList.remove('dragover');
            if (e.dataTransfer.files.length) {
                uploadFile(e.dataTransfer.files[0]);
            }
        });

        input.addEventListener('change', function() {
            if (input.files.length) {
                uploadFile(input.files[0]);
            }
        });
    }

    function uploadFile(file) {
        var zone = document.getElementById('upload-zone');
        zone.classList.add('uploading');

        var fd = new FormData();
        fd.append('file', file);

        fetch('/upload', { method: 'POST', body: fd })
            .then(function(r){ return r.json(); })
            .then(function(resp) {
                zone.classList.remove('uploading');
                if (resp.ok) {
                    // Merge new data into DATA
                    DATA[resp.month] = resp.data;
                    buildSidebar();
                    selectMonth(resp.month);
                    showNotification(resp.message, 'success');
                } else {
                    showNotification(resp.error || 'Erro no upload', 'error');
                }
            })
            .catch(function() {
                zone.classList.remove('uploading');
                showNotification('Erro de conexao com o servidor', 'error');
            });
    }

    // ---- Delete handling ----
    function setupDeleteButtons() {
        // Buttons are added dynamically in sidebar
    }

    function deleteMonth(monthKey, filename) {
        if (!confirm('Remover ' + monthKey + '?')) return;

        fetch('/api/files/' + encodeURIComponent(filename), { method: 'DELETE' })
            .then(function(r){ return r.json(); })
            .then(function(resp) {
                if (resp.ok) {
                    delete DATA[monthKey];
                    buildSidebar();
                    var first = Object.keys(DATA)[0];
                    if (first) {
                        selectMonth(first);
                    } else {
                        document.getElementById('month-title').textContent = 'Sem dados';
                        document.getElementById('month-subtitle').textContent = 'Envie um arquivo .xlsx para comecar';
                    }
                    showNotification('Arquivo removido', 'success');
                } else {
                    showNotification(resp.error || 'Erro ao remover', 'error');
                }
            });
    }

    // Override buildSidebar to include delete buttons
    var _buildSidebar = buildSidebar;
    buildSidebar = function() {
        var menu = document.getElementById('sidebar-menu');
        menu.innerHTML = '';
        var keys = Object.keys(DATA);
        if (!keys.length) {
            document.getElementById('month-count').textContent = 'Nenhum mes';
            return;
        }
        keys.forEach(function(key, i) {
            var li = document.createElement('li');
            li.classList.add('menu-item-with-delete');
            li.dataset.month = key;
            if (i === 0 && !currentMonth) li.classList.add('active');
            if (key === currentMonth) li.classList.add('active');

            var nameSpan = document.createElement('span');
            nameSpan.textContent = DATA[key].meta.display;
            nameSpan.style.cursor = 'pointer';
            nameSpan.style.flex = '1';
            nameSpan.onclick = function() { selectMonth(key); };

            var delBtn = document.createElement('span');
            delBtn.innerHTML = '&#10005;';
            delBtn.className = 'delete-btn';
            delBtn.title = 'Remover ' + DATA[key].meta.display;
            delBtn.onclick = function(e) {
                e.stopPropagation();
                deleteMonth(key, DATA[key].meta.file);
            };

            li.appendChild(nameSpan);
            li.appendChild(delBtn);
            menu.appendChild(li);
        });
        document.getElementById('month-count').textContent = keys.length + ' mes' + (keys.length > 1 ? 'es' : '');
    };

    // ---- Notifications ----
    function showNotification(msg, type) {
        var existing = document.querySelector('.notification');
        if (existing) existing.remove();

        var div = document.createElement('div');
        div.className = 'notification ' + type;
        div.textContent = msg;
        document.body.appendChild(div);
        setTimeout(function() { div.classList.add('fade-out'); }, 3000);
        setTimeout(function() { div.remove(); }, 3500);
    }

    // ---- Init ----
    function init() {
        if (typeof DATA !== 'undefined' && Object.keys(DATA).length) {
            buildSidebar();
            var first = Object.keys(DATA)[0];
            if (first) selectMonth(first);
        } else {
            document.getElementById('month-title').textContent = 'Bem-vindo';
            document.getElementById('month-subtitle').textContent = 'Envie um arquivo .xlsx para comecar o dashboard';
            buildSidebar();
        }

        setupUpload();

        var footer = document.getElementById('footer');
        if (footer) {
            footer.textContent = 'Gerado em ' + new Date().toLocaleDateString('pt-BR') + ' \u2014 Dashboard Agencia';
        }
    }

    init();
})();
