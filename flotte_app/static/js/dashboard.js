// Dashboard JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // Set current date
    const currentDate = new Date();
    const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
    document.getElementById('currentDate').textContent = currentDate.toLocaleDateString('fr-FR', options);

    // Load dashboard data
    loadDashboardData();
});

function formatCurrency(amount) {
    return new Intl.NumberFormat('fr-FR').format(amount) + ' FCFA';
}

function formatPercentage(value) {
    return value.toFixed(2) + '%';
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('fr-FR');
}

async function loadDashboardData() {
    try {
        const response = await fetch('/api/data');
        const result = await response.json();
        
        if (result.stats) {
            updateKPIs(result.stats);
            updateCamionsTable(result.stats.camions_stats);
            updateRecentTransactions(result.data);
            createCharts(result.stats.camions_stats);
        }
    } catch (error) {
        console.error('Error loading dashboard data:', error);
    }
}

function updateKPIs(stats) {
    document.getElementById('totalRevenu').textContent = formatCurrency(stats.total_revenu);
    document.getElementById('totalDepense').textContent = formatCurrency(stats.total_depense);
    
    const beneficeElement = document.getElementById('beneficeNet');
    beneficeElement.textContent = formatCurrency(stats.benefice_net);
    
    if (stats.benefice_net >= 0) {
        beneficeElement.classList.add('positive');
        beneficeElement.classList.remove('negative');
    } else {
        beneficeElement.classList.add('negative');
        beneficeElement.classList.remove('positive');
    }
    
    document.getElementById('margeMoyenne').textContent = formatPercentage(stats.marge_moyenne);
    document.getElementById('camionsActifs').textContent = `${stats.camions_actifs} / ${stats.total_camions}`;
}

function updateCamionsTable(camionsStats) {
    const tbody = document.getElementById('camionsTableBody');
    tbody.innerHTML = '';
    
    camionsStats.forEach(camion => {
        const row = document.createElement('tr');
        
        const beneficeClass = camion.benefice >= 0 ? 'positive' : 'negative';
        const margeClass = camion.marge >= 0 ? 'positive' : 'negative';
        
        row.innerHTML = `
            <td><strong>${camion.nom}</strong></td>
            <td>${formatCurrency(camion.revenu)}</td>
            <td>${formatCurrency(camion.depense)}</td>
            <td class="${beneficeClass}">${formatCurrency(camion.benefice)}</td>
            <td class="${margeClass}">${formatPercentage(camion.marge)}</td>
            <td>${camion.transactions_count}</td>
            <td>
                <a href="/camion/${camion.id}" class="btn-view">Voir détails</a>
            </td>
        `;
        
        tbody.appendChild(row);
    });
}

function updateRecentTransactions(data) {
    const container = document.getElementById('recentTransactions');
    container.innerHTML = '';
    
    // Collect all transactions from all camions
    let allTransactions = [];
    
    for (const [camionId, camionInfo] of Object.entries(data)) {
        camionInfo.transactions.forEach(t => {
            allTransactions.push({
                ...t,
                camion: camionInfo.nom
            });
        });
    }
    
    // Sort by date (most recent first)
    allTransactions.sort((a, b) => new Date(b.date) - new Date(a.date));
    
    // Show only last 10 transactions
    const recentTransactions = allTransactions.slice(0, 10);
    
    recentTransactions.forEach(transaction => {
        const item = document.createElement('div');
        item.className = 'transaction-item';
        
        const amount = transaction.revenu > 0 ? transaction.revenu : transaction.depense;
        const type = transaction.revenu > 0 ? 'revenu' : 'depense';
        const sign = transaction.revenu > 0 ? '+' : '-';
        
        item.innerHTML = `
            <div class="transaction-info">
                <div class="transaction-category">${transaction.categorie} - ${transaction.camion}</div>
                <div class="transaction-description">${transaction.description}</div>
                <div class="transaction-date">${formatDate(transaction.date)}</div>
            </div>
            <div class="transaction-amount ${type}">${sign} ${formatCurrency(amount)}</div>
        `;
        
        container.appendChild(item);
    });
}

function createCharts(camionsStats) {
    // Revenue vs Expense Chart
    const ctx1 = document.getElementById('revenueExpenseChart').getContext('2d');
    new Chart(ctx1, {
        type: 'bar',
        data: {
            labels: camionsStats.map(c => c.nom),
            datasets: [
                {
                    label: 'Revenus (FCFA)',
                    data: camionsStats.map(c => c.revenu),
                    backgroundColor: 'rgba(39, 174, 96, 0.8)',
                    borderColor: 'rgba(39, 174, 96, 1)',
                    borderWidth: 1
                },
                {
                    label: 'Dépenses (FCFA)',
                    data: camionsStats.map(c => c.depense),
                    backgroundColor: 'rgba(231, 76, 60, 0.8)',
                    borderColor: 'rgba(231, 76, 60, 1)',
                    borderWidth: 1
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'top',
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return value.toLocaleString('fr-FR') + ' FCFA';
                        }
                    }
                }
            }
        }
    });
    
    // Performance Chart (Margin %)
    const ctx2 = document.getElementById('performanceChart').getContext('2d');
    new Chart(ctx2, {
        type: 'line',
        data: {
            labels: camionsStats.map(c => c.nom),
            datasets: [{
                label: 'Marge (%)',
                data: camionsStats.map(c => c.marge),
                backgroundColor: 'rgba(52, 152, 219, 0.2)',
                borderColor: 'rgba(52, 152, 219, 1)',
                borderWidth: 2,
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'top',
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return context.parsed.y.toFixed(2) + '%';
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: false,
                    ticks: {
                        callback: function(value) {
                            return value + '%';
                        }
                    }
                }
            }
        }
    });
}
