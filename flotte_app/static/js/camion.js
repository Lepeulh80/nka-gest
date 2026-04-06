// Camion Detail Page JavaScript
let currentCamionData = null;

document.addEventListener('DOMContentLoaded', function() {
    loadCamionData();
    
    // Set default date to today
    document.getElementById('transDate').valueAsDate = new Date();
    
    // Handle form submission
    document.getElementById('addTransactionForm').addEventListener('submit', handleAddTransaction);
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

async function loadCamionData() {
    try {
        const response = await fetch(`/api/camion/${CAMION_ID}`);
        const camion = await response.json();
        
        if (camion.error) {
            alert('Erreur: ' + camion.error);
            return;
        }
        
        currentCamionData = camion;
        
        document.getElementById('camionTitle').textContent = `🚚 ${camion.nom}`;
        
        // Afficher les détails du camion
        const details = [];
        if (camion.modele) details.push(`Modèle: ${camion.modele}`);
        if (camion.chauffeur) details.push(`Chauffeur: ${camion.chauffeur}`);
        document.getElementById('camionDetails').textContent = details.join(' | ');
        
        updateCamionKPIs(camion.stats);
        updateTransactionsTable(camion.transactions);
        createTransactionsChart(camion.transactions);
    } catch (error) {
        console.error('Error loading camion data:', error);
    }
}

function updateCamionKPIs(stats) {
    document.getElementById('camionRevenu').textContent = formatCurrency(stats.revenu);
    document.getElementById('camionDepense').textContent = formatCurrency(stats.depense);
    
    const beneficeElement = document.getElementById('camionBenefice');
    beneficeElement.textContent = formatCurrency(stats.benefice);
    
    if (stats.benefice >= 0) {
        beneficeElement.classList.add('positive');
        beneficeElement.classList.remove('negative');
    } else {
        beneficeElement.classList.add('negative');
        beneficeElement.classList.remove('positive');
    }
    
    const margeElement = document.getElementById('camionMarge');
    margeElement.textContent = formatPercentage(stats.marge);
    
    if (stats.marge >= 0) {
        margeElement.classList.add('positive');
    } else {
        margeElement.classList.add('negative');
    }
}

function updateTransactionsTable(transactions) {
    const tbody = document.getElementById('transactionsTableBody');
    tbody.innerHTML = '';
    
    // Sort by date
    transactions.sort((a, b) => new Date(b.date) - new Date(a.date));
    
    transactions.forEach(transaction => {
        const row = document.createElement('tr');
        
        row.innerHTML = `
            <td>${formatDate(transaction.date)}</td>
            <td>${transaction.categorie}</td>
            <td>${transaction.description}</td>
            <td class="${transaction.revenu > 0 ? 'positive' : ''}">${transaction.revenu > 0 ? formatCurrency(transaction.revenu) : '-'}</td>
            <td class="${transaction.depense > 0 ? 'negative' : ''}">${transaction.depense > 0 ? formatCurrency(transaction.depense) : '-'}</td>
            <td>${transaction.paiement}</td>
        `;
        
        tbody.appendChild(row);
    });
}

function createTransactionsChart(transactions) {
    // Group transactions by date
    const groupedByDate = {};
    
    transactions.forEach(t => {
        const date = t.date.split(' ')[0];
        if (!groupedByDate[date]) {
            groupedByDate[date] = { revenu: 0, depense: 0 };
        }
        groupedByDate[date].revenu += t.revenu;
        groupedByDate[date].depense += t.depense;
    });
    
    const dates = Object.keys(groupedByDate).sort();
    const revenus = dates.map(d => groupedByDate[d].revenu);
    const depenses = dates.map(d => groupedByDate[d].depense);
    
    const ctx = document.getElementById('transactionsChart').getContext('2d');
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: dates.map(d => formatDate(d)),
            datasets: [
                {
                    label: 'Revenus (FCFA)',
                    data: revenus,
                    backgroundColor: 'rgba(39, 174, 96, 0.2)',
                    borderColor: 'rgba(39, 174, 96, 1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                },
                {
                    label: 'Dépenses (FCFA)',
                    data: depenses,
                    backgroundColor: 'rgba(231, 76, 60, 0.2)',
                    borderColor: 'rgba(231, 76, 60, 1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { position: 'top' },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return context.dataset.label + ': ' + context.parsed.y.toLocaleString('fr-FR') + ' FCFA';
                        }
                    }
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
}

async function handleAddTransaction(e) {
    e.preventDefault();
    
    const transaction = {
        camion_id: CAMION_ID,
        date: document.getElementById('transDate').value,
        categorie: document.getElementById('transCategorie').value,
        description: document.getElementById('transDescription').value,
        revenu: parseFloat(document.getElementById('transRevenu').value) || 0,
        depense: parseFloat(document.getElementById('transDepense').value) || 0,
        paiement: document.getElementById('transPaiement').value
    };
    
    try {
        const response = await fetch('/api/transaction', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(transaction)
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert('Transaction ajoutée avec succès!');
            document.getElementById('addTransactionForm').reset();
            document.getElementById('transDate').valueAsDate = new Date();
            document.getElementById('transRevenu').value = '0';
            document.getElementById('transDepense').value = '0';
            loadCamionData();
        } else {
            alert('Erreur: ' + result.error);
        }
    } catch (error) {
        console.error('Error adding transaction:', error);
        alert('Erreur lors de l\'ajout de la transaction');
    }
}

// Fonctions pour modifier le camion
function openEditModal() {
    if (!currentCamionData) return;
    
    document.getElementById('editNom').value = currentCamionData.nom;
    document.getElementById('editModele').value = currentCamionData.modele || '';
    document.getElementById('editChauffeur').value = currentCamionData.chauffeur || '';
    
    document.getElementById('editCamionModal').style.display = 'flex';
}

function closeEditModal() {
    document.getElementById('editCamionModal').style.display = 'none';
}

document.getElementById('editCamionModal').addEventListener('click', function(e) {
    if (e.target === this) {
        closeEditModal();
    }
});

async function handleEditCamion(e) {
    e.preventDefault();
    
    const updatedData = {
        nom: document.getElementById('editNom').value,
        modele: document.getElementById('editModele').value,
        chauffeur: document.getElementById('editChauffeur').value
    };
    
    try {
        const response = await fetch(`/api/camions/${CAMION_ID}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(updatedData)
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert('Camion modifié avec succès!');
            closeEditModal();
            loadCamionData();
        } else {
            alert('Erreur: ' + result.error);
        }
    } catch (error) {
        console.error('Error updating camion:', error);
        alert('Erreur lors de la modification du camion');
    }
}

async function deleteCamion() {
    if (!confirm('Êtes-vous sûr de vouloir supprimer ce camion ? Cette action est irréversible.')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/camions/${CAMION_ID}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert('Camion supprimé avec succès!');
            window.location.href = '/';
        } else {
            alert('Erreur: ' + result.error);
        }
    } catch (error) {
        console.error('Error deleting camion:', error);
        alert('Erreur lors de la suppression du camion');
    }
}
