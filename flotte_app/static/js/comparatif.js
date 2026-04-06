// Comparatif Page JavaScript
document.addEventListener('DOMContentLoaded', function() {
    loadComparatifData();
});

function formatCurrency(amount) {
    return new Intl.NumberFormat('fr-FR').format(amount) + ' FCFA';
}

function formatPercentage(value) {
    return value.toFixed(2) + '%';
}

async function loadComparatifData() {
    try {
        const response = await fetch('/api/data');
        const result = await response.json();
        
        if (result.stats) {
            updatePodium(result.stats.camions_stats);
            updateRankingTable(result.stats.camions_stats);
            createComparisonCharts(result.stats.camions_stats);
        }
    } catch (error) {
        console.error('Error loading comparatif data:', error);
    }
}

function updatePodium(camionsStats) {
    // Sort by margin (best first)
    const sorted = [...camionsStats].sort((a, b) => b.marge - a.marge);
    
    if (sorted.length >= 1) {
        const first = sorted[0];
        document.getElementById('podium1').querySelector('.camion-name').textContent = first.nom;
        document.getElementById('podium1').querySelector('.marge').textContent = formatPercentage(first.marge);
    }
    
    if (sorted.length >= 2) {
        const second = sorted[1];
        document.getElementById('podium2').querySelector('.camion-name').textContent = second.nom;
        document.getElementById('podium2').querySelector('.marge').textContent = formatPercentage(second.marge);
    }
    
    if (sorted.length >= 3) {
        const third = sorted[2];
        document.getElementById('podium3').querySelector('.camion-name').textContent = third.nom;
        document.getElementById('podium3').querySelector('.marge').textContent = formatPercentage(third.marge);
    }
}

function updateRankingTable(camionsStats) {
    const tbody = document.getElementById('rankingTableBody');
    tbody.innerHTML = '';
    
    // Sort by margin (best first)
    const sorted = [...camionsStats].sort((a, b) => b.marge - a.marge);
    
    sorted.forEach((camion, index) => {
        const row = document.createElement('tr');
        const rank = index + 1;
        
        let performanceBar = '';
        const maxMargin = Math.max(...sorted.map(c => Math.abs(c.marge)));
        const normalizedMargin = maxMargin > 0 ? ((camion.marge + maxMargin) / (2 * maxMargin)) * 100 : 50;
        
        performanceBar = `
            <div style="display: flex; align-items: center; gap: 10px;">
                <div style="flex: 1; background: #ecf0f1; height: 10px; border-radius: 5px; overflow: hidden;">
                    <div style="width: ${normalizedMargin}%; background: ${camion.marge >= 0 ? '#27ae60' : '#e74c3c'}; height: 100%;"></div>
                </div>
                <span style="font-size: 0.8rem;">${normalizedMargin.toFixed(0)}%</span>
            </div>
        `;
        
        row.innerHTML = `
            <td><strong>#${rank}</strong></td>
            <td>${camion.nom}</td>
            <td>${formatCurrency(camion.revenu)}</td>
            <td>${formatCurrency(camion.depense)}</td>
            <td class="${camion.benefice >= 0 ? 'positive' : 'negative'}">${formatCurrency(camion.benefice)}</td>
            <td class="${camion.marge >= 0 ? 'positive' : 'negative'}">${formatPercentage(camion.marge)}</td>
            <td>${performanceBar}</td>
        `;
        
        tbody.appendChild(row);
    });
}

function createComparisonCharts(camionsStats) {
    // Margin Comparison Chart
    const ctx1 = document.getElementById('marginComparisonChart').getContext('2d');
    new Chart(ctx1, {
        type: 'bar',
        data: {
            labels: camionsStats.map(c => c.nom),
            datasets: [{
                label: 'Marge (%)',
                data: camionsStats.map(c => c.marge),
                backgroundColor: camionsStats.map(c => c.marge >= 0 ? 'rgba(39, 174, 96, 0.8)' : 'rgba(231, 76, 60, 0.8)'),
                borderColor: camionsStats.map(c => c.marge >= 0 ? 'rgba(39, 174, 96, 1)' : 'rgba(231, 76, 60, 1)'),
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: false
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
                    ticks: {
                        callback: function(value) {
                            return value + '%';
                        }
                    }
                }
            }
        }
    });
    
    // Revenue vs Expense Chart
    const ctx2 = document.getElementById('revenueVsExpenseChart').getContext('2d');
    new Chart(ctx2, {
        type: 'doughnut',
        data: {
            labels: camionsStats.map(c => c.nom),
            datasets: [{
                label: 'Revenus',
                data: camionsStats.map(c => c.revenu),
                backgroundColor: [
                    'rgba(52, 152, 219, 0.8)',
                    'rgba(46, 204, 113, 0.8)',
                    'rgba(155, 89, 182, 0.8)',
                    'rgba(241, 196, 15, 0.8)',
                    'rgba(230, 126, 34, 0.8)'
                ],
                borderColor: [
                    'rgba(52, 152, 219, 1)',
                    'rgba(46, 204, 113, 1)',
                    'rgba(155, 89, 182, 1)',
                    'rgba(241, 196, 15, 1)',
                    'rgba(230, 126, 34, 1)'
                ],
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'bottom',
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return context.label + ': ' + context.parsed.toLocaleString('fr-FR') + ' FCFA';
                        }
                    }
                }
            }
        }
    });
    
    // Radar Chart for Complete Analysis
    const ctx3 = document.getElementById('radarChart').getContext('2d');
    new Chart(ctx3, {
        type: 'radar',
        data: {
            labels: camionsStats.map(c => c.nom),
            datasets: [
                {
                    label: 'Revenus (normalisé)',
                    data: normalizeData(camionsStats.map(c => c.revenu)),
                    backgroundColor: 'rgba(52, 152, 219, 0.2)',
                    borderColor: 'rgba(52, 152, 219, 1)',
                    borderWidth: 2,
                    pointBackgroundColor: 'rgba(52, 152, 219, 1)'
                },
                {
                    label: 'Performance (%)',
                    data: camionsStats.map(c => ((c.marge + 50) / 100) * 100), // Normalize to 0-100
                    backgroundColor: 'rgba(39, 174, 96, 0.2)',
                    borderColor: 'rgba(39, 174, 96, 1)',
                    borderWidth: 2,
                    pointBackgroundColor: 'rgba(39, 174, 96, 1)'
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
                r: {
                    beginAtZero: true,
                    max: 100,
                    ticks: {
                        stepSize: 20
                    }
                }
            }
        }
    });
}

function normalizeData(data) {
    const max = Math.max(...data);
    if (max === 0) return data.map(() => 0);
    return data.map(v => (v / max) * 100);
}
