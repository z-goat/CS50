// SPA State Management
const app = {
  currentView: 'home',
  currentMember: null,
};

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  initializeNavigation();
  loadStats();
  setupPostcodeSearch();
});

// Navigation System
function initializeNavigation() {
  document.getElementById('nav-home').addEventListener('click', (e) => {
    e.preventDefault();
    showView('home');
    updateActiveNav('nav-home');
  });

  document.getElementById('nav-research').addEventListener('click', (e) => {
    e.preventDefault();
    showView('research');
    updateActiveNav('nav-research');
  });

  document.getElementById('nav-about').addEventListener('click', (e) => {
    e.preventDefault();
    showView('about');
    updateActiveNav('nav-about');
  });

  document.getElementById('back-btn').addEventListener('click', () => {
    showView('home');
    updateActiveNav('nav-home');
  });
}

function showView(viewName) {
  // Hide all views
  document.querySelectorAll('.view').forEach(v => v.style.display = 'none');
  
  // Show selected view
  const targetView = document.getElementById(`${viewName}-view`);
  if (targetView) {
    targetView.style.display = 'block';
  }
  
  app.currentView = viewName;
}

function updateActiveNav(activeId) {
  // Remove active class from all nav links
  document.querySelectorAll('.nav-link').forEach(link => {
    link.classList.remove('active');
  });
  
  // Add active class to current nav link
  const activeLink = document.getElementById(activeId);
  if (activeLink) {
    activeLink.classList.add('active');
  }
}

// Load Database Statistics
async function loadStats() {
  try {
    const response = await fetch('/api/stats/');
    
    if (!response.ok) {
      throw new Error('Failed to fetch stats');
    }
    
    const data = await response.json();
    
    const statsHtml = `
      <div class="d-flex justify-content-around flex-wrap gap-3">
        <div class="stat-box flex-fill">
          <span class="stat-value">${data.total_members}</span>
          <div class="stat-label">MPs Tracked</div>
        </div>
        <div class="stat-box flex-fill">
          <span class="stat-value">${data.parties.length}</span>
          <div class="stat-label">Political Parties</div>
        </div>
        <div class="stat-box flex-fill">
          <span class="stat-value">${data.total_interests}</span>
          <div class="stat-label">Interests Recorded</div>
        </div>
      </div>
    `;
    
    document.getElementById('stats-container').innerHTML = statsHtml;
  } catch (err) {
    console.error('Failed to load stats:', err);
    document.getElementById('stats-container').innerHTML = 
      '<div class="alert alert-warning">Unable to load statistics</div>';
  }
}

// Postcode Search Setup
function setupPostcodeSearch() {
  const form = document.getElementById('postcode-form');
  const input = document.getElementById('postcode-input');
  const btn = document.getElementById('search-btn');
  const status = document.getElementById('search-status');

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const query = input.value.trim();
    if (!query) return;

    // Update UI - show loading state
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Searching...';
    status.innerHTML = '';

    try {
      const response = await fetch(`/api/search/?q=${encodeURIComponent(query)}`);
      const data = await response.json();

      if (response.ok) {
        if (data.in_database && data.member_id) {
          // Load full profile
          await loadMemberProfile(data.member_id);
        } else {
          // Show basic info without full profile
          showBasicMPInfo(data);
        }
      } else {
        showError(data.error || 'MP not found. Try searching by constituency name or MP name.');
      }
    } catch (err) {
      showError('Network error. Please try again.');
      console.error('Search error:', err);
    } finally {
      // Restore button state
      btn.disabled = false;
      btn.textContent = 'Search';
    }
  });
}

function showError(message) {
  const status = document.getElementById('search-status');
  status.innerHTML = `
    <div class="alert alert-warning alert-dismissible fade show" role="alert">
      <strong>Notice:</strong> ${message}
      <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    </div>
  `;
}

function showBasicMPInfo(data) {
  const status = document.getElementById('search-status');
  status.innerHTML = `
    <div class="alert alert-info alert-dismissible fade show" role="alert">
      <h5 class="alert-heading">${data.name}</h5>
      <p class="mb-1"><strong>Party:</strong> ${data.party}</p>
      <p class="mb-1"><strong>Constituency:</strong> ${data.constituency}</p>
      <hr>
      <small class="text-muted">
        This MP is not yet in our database. 
        Run <code>python manage.py seed_parliament</code> to import all MPs.
      </small>
      <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    </div>
  `;
}

// Load Member Profile
async function loadMemberProfile(memberId) {
  try {
    const response = await fetch(`/api/members/${memberId}/`);
    
    if (!response.ok) {
      showError('Failed to load MP profile');
      return;
    }
    
    const data = await response.json();
    
    app.currentMember = data;
    renderMemberProfile(data);
    showView('profile');
    updateActiveNav('nav-home'); // Keep home active since we're still in search flow
  } catch (err) {
    console.error('Failed to load profile:', err);
    showError('Network error loading profile');
  }
}

async function renderMemberProfile(member) {
  // Portrait
  const portrait = document.getElementById('mp-portrait');
  if (member.portrait_url) {
    portrait.src = member.portrait_url;
    portrait.alt = `${member.name} portrait`;
    portrait.onerror = function() {
      this.src = 'https://via.placeholder.com/150/006747/ffffff?text=' + 
                  encodeURIComponent(member.name.split(' ').map(n => n[0]).join(''));
    };
  } else {
    portrait.src = 'https://via.placeholder.com/150/006747/ffffff?text=' + 
                   encodeURIComponent(member.name.split(' ').map(n => n[0]).join(''));
  }

  // Basic info
  document.getElementById('mp-name').textContent = member.name;
  document.getElementById('mp-party').textContent = member.party;
  document.getElementById('mp-constituency').textContent = member.constituency;

  // Add party color indicator
  const partyCard = document.querySelector('#profile-view .card');
  const partyClass = getPartyClass(member.party);
  if (partyClass) {
    partyCard.classList.add(partyClass);
  }

  // Stats
  const statsHtml = `
    <div class="row g-2">
      <div class="col-6">
        <div class="stat-box">
          <span class="stat-value data-value">${member.interest_count}</span>
          <div class="stat-label">Registered<br>Interests</div>
        </div>
      </div>
      <div class="col-6">
        <div class="stat-box">
          <span class="stat-value data-value">TBD</span>
          <div class="stat-label">Conflict<br>Score</div>
        </div>
      </div>
      <div class="col-12 mt-3">
        <small class="text-muted" style="font-size: 0.75rem;">
          <strong>Last Updated:</strong> ${formatDate(member.last_updated)}
        </small>
      </div>
    </div>
  `;
  document.getElementById('mp-stats').innerHTML = statsHtml;

  // Load interests
  await loadMemberInterests(member.member_id);
}

async function loadMemberInterests(memberId) {
  const container = document.getElementById('interests-container');
  container.innerHTML = '<div class="text-center"><div class="spinner-border" role="status"></div></div>';
  
  try {
    const response = await fetch(`/api/members/${memberId}/interests/`);
    const data = await response.json();
    
    if (data.interests.length === 0) {
      container.innerHTML = `
        <div class="alert alert-info">
          <h5 class="alert-heading">No Financial Interests Recorded</h5>
          <p class="mb-0">This MP has not declared any registerable financial interests.</p>
        </div>
      `;
      return;
    }
    
    // Group interests by sector
    const bySector = {};
    data.interests.forEach(interest => {
      const sector = interest.ai_sector || 'Uncategorized';
      if (!bySector[sector]) {
        bySector[sector] = [];
      }
      bySector[sector].push(interest);
    });
    
    // Render interests
    let html = '';
    Object.keys(bySector).sort().forEach(sector => {
      const interests = bySector[sector];
      html += `
        <div class="mb-3">
          <h5 class="border-bottom pb-2 mb-2">${sector} (${interests.length})</h5>
      `;
      
      interests.forEach(interest => {
        const confidencePercent = Math.round(interest.ai_confidence * 100);
        const valueStr = interest.ai_value ? `£${interest.ai_value.toLocaleString()}` : 'Value not disclosed';
        
        html += `
          <div class="card mb-2">
            <div class="card-body p-3">
              <div class="d-flex justify-content-between align-items-start mb-2">
                <span class="badge bg-secondary">${interest.category}</span>
                ${interest.processed ? `<small class="text-muted">${confidencePercent}% confidence</small>` : '<small class="text-warning">Not processed</small>'}
              </div>
              <p class="mb-2">${interest.summary}</p>
              ${interest.ai_payer ? `<p class="mb-1"><strong>Organization:</strong> ${interest.ai_payer}</p>` : ''}
              <p class="mb-1"><strong>Estimated Value:</strong> <span class="data-value">${valueStr}</span></p>
              ${interest.registered_date ? `<small class="text-muted">Registered: ${formatDate(interest.registered_date)}</small>` : ''}
            </div>
          </div>
        `;
      });
      
      html += '</div>';
    });
    
    container.innerHTML = html;
    
  } catch (err) {
    console.error('Failed to load interests:', err);
    container.innerHTML = `
      <div class="alert alert-warning">
        Failed to load interests. Please try again.
      </div>
    `;
  }
}

// Helper function to get party CSS class
function getPartyClass(party) {
  const partyLower = party.toLowerCase();
  if (partyLower.includes('labour')) return 'party-labour';
  if (partyLower.includes('conservative')) return 'party-conservative';
  if (partyLower.includes('snp')) return 'party-snp';
  if (partyLower.includes('liberal')) return 'party-libdem';
  if (partyLower.includes('green')) return 'party-green';
  return null;
}

// Utility: Format date
function formatDate(isoString) {
  const date = new Date(isoString);
  const options = {
    day: 'numeric',
    month: 'long',
    year: 'numeric'
  };
  return date.toLocaleDateString('en-GB', options);
}

// Utility: Get CSRF token for future POST requests (Phase 2+)
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

