// Maintenance Alerts JavaScript
function getMaintenanceIcon(type) {
    const icons = {
        'vidange': '💧',
        'pneus': '🛞',
        'freins': '🛑',
        'controle_technique': '📋',
        'default': '🔧'
    };
    return icons[type] || icons['default'];
}

function getMaintenanceLabel(type) {
    const labels = {
        'vidange': 'Vidange',
        'pneus': 'Pneus',
        'freins': 'Freins',
        'controle_technique': 'Contrôle Technique'
    };
    return labels[type] || type;
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('fr-FR');
}

function displayAlerts(alerts, containerId = 'alertsContainer') {
    const alertsContainer = document.getElementById(containerId);
    
    if (!alertsContainer) return;
    
    if (alerts.length === 0) {
        alertsContainer.innerHTML = '<p style="text-align: center; color: #27ae60; padding: 2rem;">✅ Aucune alerte de maintenance - Tous les véhicules sont à jour !</p>';
        return;
    }
    
    alertsContainer.innerHTML = '';
    
    alerts.forEach(alert => {
        const alertItem = document.createElement('div');
        alertItem.className = `alert-item ${alert.priority}`;
        
        alertItem.innerHTML = `
            <div class="alert-icon">${getMaintenanceIcon(alert.maintenance_type)}</div>
            <div class="alert-content">
                <div class="alert-title">${alert.camion_nom || 'Camion'} - ${getMaintenanceLabel(alert.maintenance_type)}</div>
                <div class="alert-message">${alert.message}</div>
                <div class="alert-meta">
                    <span>Dernière: ${formatDate(alert.date_derniere)}</span>
                    <span>Prochaine: ${formatDate(alert.date_prochaine)}</span>
                    <span class="alert-badge">${alert.status}</span>
                </div>
            </div>
            <button class="btn-mark-done" onclick="markMaintenanceDone('${alert.camion_id}', '${alert.maintenance_type}')">
                ✓ Marquer comme fait
            </button>
        `;
        
        alertsContainer.appendChild(alertItem);
    });
}

async function markMaintenanceDone(camionId, maintenanceType) {
    if (!confirm(`Confirmer que la maintenance "${getMaintenanceLabel(maintenanceType)}" a été effectuée pour ${camionId} ?`)) {
        return;
    }
    
    try {
        const response = await fetch('/api/maintenance/update', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                camion_id: camionId,
                maintenance_type: maintenanceType
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert('✅ Maintenance mise à jour avec succès !');
            // Recharger la page pour actualiser les alertes
            location.reload();
        } else {
            alert('❌ Erreur: ' + result.error);
        }
    } catch (error) {
        console.error('Error updating maintenance:', error);
        alert('❌ Erreur lors de la mise à jour de la maintenance');
    }
}

async function loadMaintenanceAlerts() {
    try {
        const response = await fetch('/api/alerts');
        const result = await response.json();
        
        if (result.alerts) {
            displayAlerts(result.alerts);
        }
    } catch (error) {
        console.error('Error loading maintenance alerts:', error);
    }
}
