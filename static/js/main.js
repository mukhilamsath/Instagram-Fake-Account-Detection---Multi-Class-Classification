document.addEventListener('DOMContentLoaded', () => {

  // ── Real dataset medians per class ─────────────────────────────────────
  // r: posts=28, followers=609, following=394, bio_len=43, picture=1, link=0
  // a: posts=61, followers=2000, following=437, bio_len=25, picture=1, link=0
  // i: posts=1,  followers=3900, following=88,  bio_len=0,  picture=1, link=0
  // s: posts=51, followers=1800, following=357, bio_len=34, picture=1, link=0
  const EXAMPLES = {
    r: { no_of_posts: 28,  followers: 609,  following: 394, bio_len: 43, picture: '1', link: '0' },
    a: { no_of_posts: 61,  followers: 2000, following: 437, bio_len: 25, picture: '1', link: '0' },
    i: { no_of_posts: 1,   followers: 3900, following: 88,  bio_len: 0,  picture: '1', link: '0' },
    s: { no_of_posts: 51,  followers: 1800, following: 357, bio_len: 34, picture: '1', link: '0' },
  };

  window.loadExample = function(cls) {
    const ex = EXAMPLES[cls];
    if (!ex) return;
    document.getElementById('no_of_posts').value = ex.no_of_posts;
    document.getElementById('followers').value   = ex.followers;
    document.getElementById('following').value   = ex.following;
    document.getElementById('bio_len').value     = ex.bio_len;
    document.getElementById('picture').value     = ex.picture;
    document.getElementById('link').value        = ex.link;
    // Auto-submit after a short delay so the user sees the values load
    setTimeout(() => document.getElementById('scan-form').requestSubmit(), 300);
  };

  const form        = document.getElementById('scan-form');
  const scanBtn     = document.getElementById('scan-btn');
  const btnLabel    = document.getElementById('btn-label');
  const btnSpinner  = document.getElementById('btn-spinner');
  const resultPanel = document.getElementById('result-panel');

  const resultIcon   = document.getElementById('result-icon');
  const resultLabel  = document.getElementById('result-label');
  const resultClass  = document.getElementById('result-class');
  const resultBadge  = document.getElementById('result-badge');
  const resultModel  = document.getElementById('result-model-tag');

  // Signal bar fills
  const sfillPosts   = document.getElementById('sfill-posts');
  const sfillRatio   = document.getElementById('sfill-ratio');
  const sfillBio     = document.getElementById('sfill-bio');
  const sfillPicture = document.getElementById('sfill-picture');

  // Class mapping for display
  const classConfig = {
    'r': { icon: '✅', colour: 'var(--green)',  badge: 'badge-r', label: 'Real Account'    },
    'a': { icon: '⚠️', colour: 'var(--yellow)', badge: 'badge-a', label: 'Active Fake'     },
    'i': { icon: '👻', colour: 'var(--blue)',   badge: 'badge-i', label: 'Inactive Fake'   },
    's': { icon: '🤖', colour: 'var(--red)',    badge: 'badge-s', label: 'Spammer Fake'    }
  };

  // Clamp a value between 0 and 1 for bar percentage
  function clamp01(v, max) { return Math.min(Math.max(v / (max || 1), 0), 1); }

  function setLoading(state) {
    scanBtn.disabled = state;
    btnLabel.textContent = state ? 'Scanning…' : 'Scan Account';
    state ? btnSpinner.classList.remove('hidden') : btnSpinner.classList.add('hidden');
  }

  function showResult(data, formValues) {
    const cfg = classConfig[data.predicted_class] || { icon: '❓', colour: '#fff', badge: '', label: 'Unknown' };

    // Re-trigger pop animation
    resultIcon.style.animation = 'none';
    requestAnimationFrame(() => {
      resultIcon.style.animation = '';
      resultIcon.textContent = cfg.icon;
    });

    resultLabel.textContent = data.meaning;
    resultLabel.style.cssText = '';   // reset any inline overrides
    resultClass.textContent = `Class code: "${data.predicted_class}"`;

    // Badge
    resultBadge.textContent = cfg.label;
    resultBadge.className = `result-badge ${cfg.badge}`;

    resultModel.textContent = `Powered by ${data.model_used}`;

    // Signal bars (simple heuristics for visual indication)
    const posts      = parseFloat(formValues.no_of_posts) || 0;
    const followers  = parseFloat(formValues.followers)   || 0;
    const following  = parseFloat(formValues.following)   || 0;
    const bio        = parseFloat(formValues.bio_len)     || 0;
    const picture    = parseFloat(formValues.picture)     || 0;

    const ratio = following > 0 ? followers / following : 1;

    sfillPosts.style.width   = `${Math.min(posts / 200, 1) * 100}%`;
    sfillRatio.style.width   = `${Math.min(ratio, 1) * 100}%`;
    sfillBio.style.width     = `${Math.min(bio / 300, 1) * 100}%`;
    sfillPicture.style.width = `${picture * 100}%`;

    // Show panel with slide-in
    resultPanel.classList.remove('hidden');
    resultPanel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    setLoading(true);

    const formData = new FormData(form);
    const formValues = Object.fromEntries(formData.entries());

    try {
      const res = await fetch('/predict', { method: 'POST', body: formData });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      showResult(data, formValues);
    } catch (err) {
      console.error('Prediction error:', err);
      resultPanel.classList.remove('hidden');
      resultIcon.textContent = '❌';
      resultLabel.textContent = 'Error';
      resultLabel.style.color = 'var(--red)';
      resultClass.textContent = 'Server error — check the terminal logs.';
      resultBadge.textContent = '';
      resultModel.textContent = '';
    } finally {
      setLoading(false);
    }
  });

  // Subtle focus lift on number inputs
  document.querySelectorAll('.field-input[type="number"]').forEach(inp => {
    inp.addEventListener('focus', () => inp.closest('.field-group').style.transform = 'translateY(-2px)');
    inp.addEventListener('blur',  () => inp.closest('.field-group').style.transform = '');
  });
});
