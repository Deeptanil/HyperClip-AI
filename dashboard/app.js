/**
 * HyperClip AI // Dashboard Application Logic
 * Minimalist Dark Ops Control Center (Emoji-Free, Strict SVG/Text)
 */

(function () {
  'use strict';

  // --- Safe LocalStorage Access ---
  const STORAGE_KEY_AUTH = 'hyperclip_auth_config';
  const STORAGE_KEY_SETTINGS = 'hyperclip_local_settings';
  const STORAGE_KEY_OVERRIDES = 'hyperclip_clip_overrides_v2';

  function safeGetStorage(key, defaultVal) {
    try {
      const item = localStorage.getItem(key);
      if (!item || item === 'undefined' || item === 'null') return defaultVal;
      return JSON.parse(item);
    } catch (e) {
      console.warn('Storage read fallback for key:', key, e);
      return defaultVal;
    }
  }

  function safeSetStorage(key, val) {
    try {
      localStorage.setItem(key, JSON.stringify(val));
    } catch (e) {
      console.warn('Storage write failed for key:', key, e);
    }
  }

  function getLocalOverrides() {
    return safeGetStorage(STORAGE_KEY_OVERRIDES, {});
  }

  function getOverrideKey(clip) {
    if (!clip) return '';
    if (clip.filename) return String(clip.filename).replace(/\.mp4$/i, '').replace(/\.json$/i, '');
    if (clip.id) return String(clip.id).replace(/^real_/, '');
    return '';
  }

  function saveLocalOverride(clip, changes) {
    const key = getOverrideKey(clip);
    if (!key) return;
    const overrides = getLocalOverrides();
    overrides[key] = {
      ...(overrides[key] || {}),
      ...changes,
      updated_at: Date.now()
    };
    safeSetStorage(STORAGE_KEY_OVERRIDES, overrides);
  }

  function removeLocalOverride(clip) {
    const key = getOverrideKey(clip);
    if (!key) return;
    const overrides = getLocalOverrides();
    delete overrides[key];
    safeSetStorage(STORAGE_KEY_OVERRIDES, overrides);
  }

  function applyOverridesToClip(clip) {
    if (!clip) return;
    const key = getOverrideKey(clip);
    const overrides = getLocalOverrides();
    const ov = overrides[key];
    if (ov) {
      if (ov.permanently_deleted) {
        clip._deleted = true;
        return;
      }
      if (typeof ov.discarded === 'boolean') {
        clip.discarded = ov.discarded;
      }
      if (ov.discarded_at !== undefined) {
        clip.discarded_at = ov.discarded_at;
      }
      if (ov.pre_discard_priority !== undefined) {
        clip.pre_discard_priority = ov.pre_discard_priority;
      }
      if (ov.priority !== undefined) {
        clip.priority = parseInt(ov.priority, 10);
      }
      if (ov.title) {
        clip.title = ov.title;
      }
      if (ov.caption) {
        clip.caption = ov.caption;
      }
    }
  }

  let auth = safeGetStorage(STORAGE_KEY_AUTH, {
    pat: '',
    repo: 'Deeptanil/HyperClip-AI',
    branch: 'master',
    contentBranch: 'content',
    isDemo: true
  });

  function safeInt(val, fallback) {
    const n = parseInt(val, 10);
    return Number.isNaN(n) ? fallback : n;
  }

  let settings = safeGetStorage(STORAGE_KEY_SETTINGS, {
    ig1Posts: 2,
    ig1TrialPosts: 1,
    ig2Posts: 2,
    ytPosts: 3,
    hypeMode: false,
    streamYield: 10,
    clipSpacing: 300,
    prioritizedCategories: ['Grand Theft Auto VI', 'GTA 6', 'GTA VI'],
    deprioritizedCategories: [],
    autoCensorNsfw: true,
    censorMode: 'blur',
    tokenExpiryDate: '2027-01-17'
  });

  settings.ig1Posts = Math.max(0, safeInt(settings.ig1Posts, 2));
  settings.ig2Posts = Math.max(0, safeInt(settings.ig2Posts, 2));
  settings.ytPosts = Math.max(0, safeInt(settings.ytPosts, 3));
  settings.ig1TrialPosts = Math.min(settings.ig1Posts, Math.max(0, safeInt(settings.ig1TrialPosts, 1)));
  if (!settings.tokenExpiryDate) {
    settings.tokenExpiryDate = '2027-01-17';
  }
  if (!Array.isArray(settings.prioritizedCategories)) {
    settings.prioritizedCategories = ['Grand Theft Auto VI', 'GTA 6', 'GTA VI'];
  }
  if (!Array.isArray(settings.deprioritizedCategories)) {
    settings.deprioritizedCategories = [];
  }
  if (typeof settings.autoCensorNsfw !== 'boolean') {
    settings.autoCensorNsfw = true;
  }
  if (!settings.censorMode) {
    settings.censorMode = 'blur';
  }

  let activeTab = 'calendar';
  let isSettingsDirty = false;
  let activeCalView = 'week'; // 'day', 'week', 'month'
  let activeFilter = 'all'; // 'all', 'ig1', 'ig2', 'youtube', 'staged'
  let activePrioFilter = 'all'; // 'all', '5', '4', '3', '2', '1'
  let currentDate = new Date();
  let selectedClip = null;
  let lastTodayCounts = { ig1: 0, ig2: 0, youtube: 0 };

  // --- 5-Tier Posting Priority System (1 to 5, 5 being highest, 1 being lowest) ---
  // 5: Highest (manual only)
  // 4: Prioritized (matches prioritized categories like GTA 6, or manual)
  // 3: Default (standard clips)
  // 2: Unprioritized (matches deprioritized categories, or manual)
  // 1: Lowest (manual only)
  // Discarded clips (discarded: true) are routed to Discarded tab with a 6-hour deletion timer
  function getClipPriority(clip) {
    if (clip.discarded) {
      return { priority: 0, rank: 99, tier: 'discarded', label: 'Discarded', isDiscarded: true };
    }

    const explicit = clip.priority;
    if (typeof explicit === 'number' && explicit >= 1 && explicit <= 5) {
      const labels = {
        5: 'P5 (Highest)',
        4: 'P4 (Prioritized)',
        3: 'P3 (Default)',
        2: 'P2 (Unprioritized)',
        1: 'P1 (Lowest)'
      };
      return { priority: explicit, rank: 6 - explicit, tier: String(explicit), label: labels[explicit], source: 'manual' };
    }
    if (typeof explicit === 'string' && /^[1-5]$/.test(explicit.trim())) {
      const p = parseInt(explicit.trim(), 10);
      const labels = {
        5: 'P5 (Highest)',
        4: 'P4 (Prioritized)',
        3: 'P3 (Default)',
        2: 'P2 (Unprioritized)',
        1: 'P1 (Lowest)'
      };
      return { priority: p, rank: 6 - p, tier: String(p), label: labels[p], source: 'manual' };
    }
    if (String(explicit).toLowerCase().trim() === 'prioritized') {
      return { priority: 4, rank: 2, tier: '4', label: 'P4 (Prioritized)', source: 'manual' };
    }
    if (['deprioritized', 'unprioritized'].includes(String(explicit).toLowerCase().trim())) {
      return { priority: 2, rank: 4, tier: '2', label: 'P2 (Unprioritized)', source: 'manual' };
    }

    const prioCats = (settings.prioritizedCategories || []).map(c => String(c).toLowerCase().trim()).filter(Boolean);
    const deprioCats = (settings.deprioritizedCategories || []).map(c => String(c).toLowerCase().trim()).filter(Boolean);
    const haystack = [
      clip.game || '',
      clip.category || '',
      clip.title || '',
      clip.caption || '',
      clip.filename || ''
    ].join(' ').toLowerCase();

    const matchedPrio = prioCats.find(cat => haystack.includes(cat));
    if (matchedPrio) {
      return { priority: 4, rank: 2, tier: '4', label: `P4 (${matchedPrio.toUpperCase()})`, source: 'category' };
    }
    const matchedDeprio = deprioCats.find(cat => haystack.includes(cat));
    if (matchedDeprio) {
      return { priority: 2, rank: 4, tier: '2', label: `P2 (${matchedDeprio.toUpperCase()})`, source: 'category' };
    }
    return { priority: 3, rank: 3, tier: '3', label: 'P3 (Default)', source: 'default' };
  }

  function getClipTimestamp(c) {
    if (c.timestamp) {
      const t = new Date(c.timestamp).getTime();
      if (!Number.isNaN(t)) return t;
    }
    const m = (c.filename || '').match(/^(\d{4}-\d{2}-\d{2})/);
    if (m) {
      const t = new Date(m[1]).getTime();
      if (!Number.isNaN(t)) return t;
    }
    return 0;
  }

  function sortPipelineClips() {
    pipelineClips.forEach(c => {
      c._prio = getClipPriority(c);
    });
    // Active clips first by priority DESC (5 first, then 4, 3, 2, 1), then FIFO
    // Discarded clips placed at the end
    pipelineClips.sort((a, b) => {
      if (Boolean(a.discarded) !== Boolean(b.discarded)) {
        return a.discarded ? 1 : -1;
      }
      const pDiff = (b._prio?.priority ?? 3) - (a._prio?.priority ?? 3);
      if (pDiff !== 0) return pDiff;
      return getClipTimestamp(a) - getClipTimestamp(b);
    });
  }

  function formatSliderVal(val) {
    const n = safeInt(val, 0);
    return n === 0 ? '0 (OFF)' : String(n);
  }

  function updateTopStatCards() {
    const ig1ValEl = document.getElementById('ig1-stat-val');
    const ig2ValEl = document.getElementById('ig2-stat-val');
    const ytValEl = document.getElementById('yt-stat-val');

    if (ig1ValEl) {
      ig1ValEl.innerHTML = `${lastTodayCounts.ig1} / ${settings.ig1Posts} <small class="text-dim-unit">${settings.ig1Posts === 0 ? 'paused' : 'in 24h'}</small>`;
    }
    if (ig2ValEl) {
      ig2ValEl.innerHTML = `${lastTodayCounts.ig2} / ${settings.ig2Posts} <small class="text-dim-unit">${settings.ig2Posts === 0 ? 'paused' : 'in 24h'}</small>`;
    }
    if (ytValEl) {
      ytValEl.innerHTML = `${lastTodayCounts.youtube} / ${settings.ytPosts} <small class="text-dim-unit">${settings.ytPosts === 0 ? 'paused' : 'in 24h'}</small>`;
    }
  }

  // Data collections
  let pipelineClips = [];
  let postedClips = [];
  let scheduledSlots = [];
  const clipBlobCache = new Map(); // bounded cache for loaded clip blobs
  let activePreviewAbortController = null;
  let isPreviewModalActive = false;
  let pendingRenderAfterModal = false;
  let lastSyncSignature = '';
  const metadataCacheBySha = new Map(); // jsonSha -> parsedMetadata cache

  // --- Clean SVG Icon Helpers (No Emojis) ---
  const ICONS = {
    check: '<svg class="icon icon-sm" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"/></svg>',
    play: '<svg class="icon icon-sm" viewBox="0 0 24 24"><polygon points="5 3 19 12 5 21 5 3"/></svg>',
    clock: '<svg class="icon icon-sm" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>',
    alert: '<svg class="icon icon-sm" viewBox="0 0 24 24"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
    film: '<svg class="icon icon-lg" viewBox="0 0 24 24"><polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>'
  };

  // --- Demo Dataset (No Emojis, Real Streamer Clips) ---
  const DEMO_PIPELINE = [
    {
      id: 'clip_xqc_cs',
      filename: '2026-11-15-xqc_cs_1v3_clutch.mp4',
      path: 'output/stream_pipeline/2026-11-15-xqc_cs_1v3_clutch.mp4',
      streamer: 'xQc',
      title: 'xQc 1v3 Counter-Strike Clutch',
      caption: 'xQc clutches insane 1v3 live in Counter-Strike! #xqc #cs2 #gaming #twitchclips #shorts',
      duration: '0:38',
      durationSec: 38,
      sigma: '4.8 σ',
      motion: 'Delta 24.1% (High Action)',
      layout: 'Dual Stack 9:16',
      target: 'Instagram (loopablez)',
      account: 'ig2',
      isTrial: false,
      status: 'staged',
      videoUrl: 'https://raw.githubusercontent.com/Deeptanil/HyperClip-AI/content/output/stream_pipeline/2026-11-15-xqc_cs_1v3_clutch.mp4'
    },
    {
      id: 'clip_kai_malenia',
      filename: '2026-11-15-kai_cenat_malenia_clutch.mp4',
      path: 'output/stream_pipeline/2026-11-15-kai_cenat_malenia_clutch.mp4',
      streamer: 'Kai Cenat',
      title: 'Kai Cenat Beats Malenia After 431 Deaths',
      caption: 'After 431+ attempts and 50+ hours Kai Cenat finally defeats Malenia live on stream! #kaicenat #eldenring #malenia #twitchclips #gaming #shorts #reels',
      duration: '0:28',
      durationSec: 28,
      sigma: '4.9 σ',
      motion: 'Delta 28.5% (Victory Moment)',
      layout: 'Dual Stack 9:16',
      target: 'Instagram (solvikz) [Trial Reel] & YouTube',
      account: 'ig1',
      isTrial: true,
      status: 'staged',
      videoUrl: 'https://raw.githubusercontent.com/Deeptanil/HyperClip-AI/content/output/stream_pipeline/2026-11-15-kai_cenat_malenia_clutch.mp4'
    },
    {
      id: 'clip_caseoh_terror',
      filename: '2026-11-15-caseoh_lethal_company_scream.mp4',
      path: 'output/stream_pipeline/2026-11-15-caseoh_lethal_company_scream.mp4',
      streamer: 'CaseOh',
      title: 'CaseOh Terrified on Lethal Company',
      caption: 'CaseOh cannot survive 5 minutes in Lethal Company facility! #caseoh #lethalcompany #gaming #twitchclips #shorts',
      duration: '0:32',
      durationSec: 32,
      sigma: '4.5 σ',
      motion: 'Delta 21.0% (Terrified)',
      layout: 'Dual Stack 9:16',
      target: 'YouTube Shorts',
      account: 'youtube',
      isTrial: false,
      status: 'staged',
      videoUrl: 'https://raw.githubusercontent.com/Deeptanil/HyperClip-AI/content/output/stream_pipeline/2026-11-15-caseoh_lethal_company_scream.mp4'
    }
  ];

  const DEMO_POSTED = [
    {
      id: 'posted_clix_1',
      title: 'Clix Goes Crazy on Fortnite',
      account: 'ig2',
      platform: 'Instagram (loopablez)',
      date: new Date(Date.now() - 4 * 3600 * 1000).toISOString(),
      url: 'https://instagram.com/reel/DfwZVNOR_Ch',
      status: 'posted'
    },
    {
      id: 'posted_speed_1',
      title: 'IShowSpeed Stream Clip',
      account: 'ig2',
      platform: 'Instagram (loopablez)',
      date: new Date(Date.now() - 8 * 3600 * 1000).toISOString(),
      url: 'https://instagram.com/reel/DfwZYQhx3Br',
      status: 'posted'
    },
    {
      id: 'posted_yt_1',
      title: 'Apex Legends 1v4 Short Highlight',
      account: 'youtube',
      platform: 'YouTube Shorts',
      date: new Date(Date.now() - 14 * 3600 * 1000).toISOString(),
      url: 'https://youtube.com/shorts',
      status: 'posted'
    }
  ];

  // --- Meta Token Expiry & Warning System ---
  function calculateDaysUntilExpiry(dateStr) {
    if (!dateStr) return null;
    const parts = String(dateStr).trim().split('-');
    if (parts.length !== 3) return null;
    const exp = new Date(parseInt(parts[0], 10), parseInt(parts[1], 10) - 1, parseInt(parts[2], 10));
    if (isNaN(exp.getTime())) return null;
    const now = new Date();
    exp.setHours(0, 0, 0, 0);
    now.setHours(0, 0, 0, 0);
    const diffMs = exp.getTime() - now.getTime();
    return Math.round(diffMs / (1000 * 60 * 60 * 24));
  }

  function renderTokenExpiryAlerts() {
    const banner = document.getElementById('token-expiry-banner');
    const statusBox = document.getElementById('token-lifecycle-status-box');
    const inputDate = document.getElementById('input-token-expiry');
    const diagIg1 = document.getElementById('diag-ig1-token-expiry');
    const diagIg2 = document.getElementById('diag-ig2-token-expiry');

    const expDate = settings.tokenExpiryDate || '2027-01-17';
    if (inputDate && (!inputDate.value || inputDate.value !== expDate)) {
      inputDate.value = expDate;
    }
    if (diagIg1) diagIg1.textContent = expDate;
    if (diagIg2) diagIg2.textContent = expDate;

    const daysLeft = calculateDaysUntilExpiry(expDate);
    if (daysLeft === null) {
      if (banner) banner.style.display = 'none';
      return;
    }

    if (daysLeft <= 0) {
      // CRITICAL ERROR: Token expired!
      if (banner) {
        banner.className = 'token-alert-banner banner-critical';
        banner.style.display = 'flex';
        banner.innerHTML = `
          <div class="banner-icon"><svg class="icon icon-lg" viewBox="0 0 24 24"><polygon points="7.86 2 16.14 2 22 7.86 22 16.14 16.14 22 7.86 22 2 16.14 2 7.86 7.86 2"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg></div>
          <div class="banner-body">
            <strong>CRITICAL ERROR: Meta Graph API Token Expired (${expDate})</strong>
            <span>Automatic Instagram Reels posting is stopped to prevent failed API calls. Please generate a fresh long-lived token in Meta Graph Explorer and update repository secrets.</span>
          </div>
          <button class="btn btn-sm btn-critical" onclick="document.getElementById('tab-nav-accounts').click();">Resolve in Accounts</button>
        `;
      }
      if (statusBox) {
        statusBox.style.borderColor = 'var(--danger)';
        statusBox.style.background = 'rgba(239, 68, 68, 0.12)';
        statusBox.innerHTML = `
          <div>
            <div style="font-weight:700;color:var(--danger);font-size:13px;">CRITICAL: Token Expired on ${expDate} (${Math.abs(daysLeft)} day${Math.abs(daysLeft) === 1 ? '' : 's'} ago)</div>
            <div style="color:var(--text-muted);font-size:12px;margin-top:2px;">Reels publishing is suspended. Generate a new token and update GitHub secrets.</div>
          </div>
          <span class="status-pill error"><span class="dot offline"></span> EXPIRED</span>
        `;
      }
    } else if (daysLeft <= 30) {
      // WARNING: Expiring within 1 month (30 days)
      if (banner) {
        banner.className = 'token-alert-banner banner-warning';
        banner.style.display = 'flex';
        banner.innerHTML = `
          <div class="banner-icon"><svg class="icon icon-lg" viewBox="0 0 24 24"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg></div>
          <div class="banner-body">
            <strong>WARNING: Meta Graph API Token Expires in ${daysLeft} Day${daysLeft === 1 ? '' : 's'} (${expDate})</strong>
            <span>Your token expires in less than 30 days. Please refresh your long-lived token in Meta Graph API Explorer soon to prevent publishing interruptions.</span>
          </div>
          <button class="btn btn-sm btn-yellow" onclick="document.getElementById('tab-nav-accounts').click();">Update Expiry Date</button>
        `;
      }
      if (statusBox) {
        statusBox.style.borderColor = 'var(--yellow)';
        statusBox.style.background = 'rgba(250, 204, 21, 0.10)';
        statusBox.innerHTML = `
          <div>
            <div style="font-weight:700;color:var(--yellow);font-size:13px;">Warning: Expires in ${daysLeft} days (${expDate})</div>
            <div style="color:var(--text-muted);font-size:12px;margin-top:2px;">Approaching 30-day cutoff window. Extend your token in Meta Developer Portal.</div>
          </div>
          <span class="status-pill warning"><span class="dot yellow"></span> Expires in ${daysLeft}d</span>
        `;
      }
    } else {
      // HEALTHY: More than 30 days remaining
      if (banner) {
        banner.style.display = 'none';
      }
      if (statusBox) {
        statusBox.style.borderColor = 'var(--border)';
        statusBox.style.background = 'var(--bg-elevated)';
        statusBox.innerHTML = `
          <div>
            <div style="font-weight:700;color:var(--success);font-size:13px;">Healthy: Token valid until ${expDate} (${daysLeft} days remaining)</div>
            <div style="color:var(--text-muted);font-size:12px;margin-top:2px;">Automatic warning will activate on ${new Date(Date.now() + (daysLeft - 30) * 86400000).toISOString().split('T')[0]} (1 month before expiry).</div>
          </div>
          <span class="status-pill"><span class="dot online"></span> ${daysLeft} Days Remaining</span>
        `;
      }
    }
  }

  // --- Dynamic Spacing & Hazard Detection ---
  function calculateDynamicSpacing() {
    const ig1N = safeInt(settings.ig1Posts, 0);
    const ig2N = safeInt(settings.ig2Posts, 0);
    const ytN = safeInt(settings.ytPosts, 0);
    const totalIg = ig1N + ig2N;
    const intervalHours = totalIg > 0 ? (24 / totalIg) : 0;
    const intervalMins = Math.round(intervalHours * 60);

    const minPerAccountHours = 3.0; // Strict anti-shadowban
    const minCrossAccountMins = 25; // Anti-bot IP safeguard

    const summaryEl = document.getElementById('spacing-summary-text');
    if (summaryEl) {
      const trial1 = Math.min(ig1N, safeInt(settings.ig1TrialPosts, 0));
      const reg1 = Math.max(0, ig1N - trial1);
      const ytGapText = ytN > 0
        ? `1 Short every <strong>${(24 / ytN).toFixed(1)}h</strong> (minus 1.5h buffer)`
        : `<strong style="color:var(--danger)">Paused (0 Shorts/day)</strong>`;
      const igGapText = totalIg > 0
        ? `1 Reel every <strong>${intervalHours.toFixed(1)} hours (${intervalMins} mins)</strong> across active IG slots (≥ ${minCrossAccountMins}m cross-account buffer)`
        : `<strong style="color:var(--danger)">Instagram Paused (0 Reels/day)</strong>`;

      summaryEl.innerHTML = `
        <strong>Dynamic Spacing Plan:</strong> ${totalIg} Instagram Reels/day (${ig1N} @solvikz [${trial1} trial, ${reg1} standard] + ${ig2N} @loopablez) + ${ytN} YouTube Shorts/day.<br>
        • <strong>Instagram Cadence:</strong> ${igGapText}<br>
        • <strong>YouTube Cadence:</strong> ${ytGapText}<br>
        • <strong>Priority Order:</strong> 5 (Highest) → 4 (Prioritized, ${(settings.prioritizedCategories || []).length} rules) → 3 (Default) → 2 (Unprioritized, ${(settings.deprioritizedCategories || []).length} rules) → 1 (Lowest).
      `;
    }

    // Shadowban Hazard Warning Alert
    const hazardBox = document.getElementById('shadowban-hazard-box');
    const hazardTitle = document.getElementById('shadowban-hazard-title');
    const hazardDesc = document.getElementById('shadowban-hazard-desc');

    const maxPostsSingleAccount = Math.max(ig1N, ig2N);
    const minCalculatedGap = maxPostsSingleAccount > 0 ? (24 / maxPostsSingleAccount) : 24;

    if (hazardBox) {
      if (maxPostsSingleAccount > 0 && (minCalculatedGap < 3.0 || maxPostsSingleAccount >= 5)) {
        hazardBox.style.display = 'flex';
        hazardBox.className = 'danger-box';
        if (hazardTitle) hazardTitle.innerText = 'CRITICAL SPAM HAZARD: FREQUENCY LIMIT EXCEEDED';
        if (hazardDesc) {
          hazardDesc.innerHTML = `
            <strong>WARNING: High risk of account restriction / shadowban.</strong> An Instagram account is set to <strong>${maxPostsSingleAccount} posts/day</strong>, which drops the post separation down to only <strong>${minCalculatedGap.toFixed(1)} hours</strong>.<br>
            Instagram's anti-spam detection automatically restricts accounts posting with less than a 3.0-hour gap or more than 4 times per day.<br>
            <em>Recommendation: Reduce daily posts to ≤ 3 per account to maintain a safe 4.0h+ cooldown.</em>
          `;
        }
      } else if (maxPostsSingleAccount === 4 || (maxPostsSingleAccount > 0 && minCalculatedGap < 4.0)) {
        hazardBox.style.display = 'flex';
        hazardBox.className = 'danger-box warning-yellow';
        if (hazardTitle) hazardTitle.innerText = 'MODERATE SPAM RISK: ELEVATED POST FREQUENCY';
        if (hazardDesc) {
          hazardDesc.innerHTML = `
            <strong>Caution: Elevated post frequency (${maxPostsSingleAccount} posts/day, ~${minCalculatedGap.toFixed(1)}h gap).</strong><br>
            This rate should only be enabled temporarily for hype weekend events. Sustained posting above 3 reels/day on new accounts may suppress Explore page reach.
          `;
        }
      } else {
        hazardBox.style.display = 'none';
      }
    }

    updateTopStatCards();
    updateCooldownDisplays();
    generateScheduledSlots();
  }

  function generateScheduledSlots() {
    scheduledSlots = [];
    const ig1Count = Math.max(0, parseInt(settings.ig1Posts, 10) || 0);
    const ig2Count = Math.max(0, parseInt(settings.ig2Posts, 10) || 0);
    const ytCount = Math.max(0, parseInt(settings.ytPosts, 10) || 0);

    const totalIg = ig1Count + ig2Count;

    // 1. Instagram Slots: Interleave ig1 and ig2 spaced across 24h
    if (totalIg > 0) {
      const stepMinutes = Math.floor((24 * 60) / totalIg);
      let ig1Allocated = 0;
      let ig1TrialAllocated = 0;
      let ig2Allocated = 0;
      const ig1TrialTarget = Math.max(0, parseInt(settings.ig1TrialPosts, 10) || 0);

      for (let i = 0; i < totalIg; i++) {
        const totalMinutes = i * stepMinutes;
        const h = Math.floor(totalMinutes / 60) % 24;
        const m = totalMinutes % 60;

        let acc = 'ig1';
        if (ig1Allocated < ig1Count && ig2Allocated < ig2Count) {
          acc = (i % 2 === 0) ? 'ig1' : 'ig2';
        } else if (ig1Allocated < ig1Count) {
          acc = 'ig1';
        } else {
          acc = 'ig2';
        }

        let isTrial = false;
        if (acc === 'ig1') {
          ig1Allocated++;
          if (ig1TrialAllocated < ig1TrialTarget) {
            isTrial = true;
            ig1TrialAllocated++;
          }
        } else {
          ig2Allocated++;
        }

        const isIg1 = acc === 'ig1';
        scheduledSlots.push({
          id: `sched_ig_${i}`,
          hour: h,
          minute: m,
          timeMinutes: totalMinutes,
          timeStr: `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`,
          account: acc,
          platform: isIg1 ? 'Instagram (@solvikz)' : 'Instagram (@loopablez)',
          title: isTrial ? `Scheduled Trial Reel (${isIg1 ? 'solvikz' : 'loopablez'})` : `Scheduled Reel (${isIg1 ? 'solvikz' : 'loopablez'})`,
          status: 'scheduled',
          isTrial: isTrial
        });
      }
    }

    // 2. YouTube Shorts Slots: Spaced across 24h, intelligently staggered from IG slots
    if (ytCount > 0) {
      const stepYt = Math.floor((24 * 60) / ytCount);
      const igMinutes = scheduledSlots.map(s => s.timeMinutes);

      // Find an offset that maximizes circular distance to all existing Instagram slots
      let bestOffset = Math.floor(stepYt / 2);
      let maxMinDist = -1;
      for (let candOffset = 15; candOffset < stepYt; candOffset += 15) {
        let minDist = 9999;
        for (let j = 0; j < ytCount; j++) {
          const ytM = (j * stepYt + candOffset) % (24 * 60);
          for (const igM of igMinutes) {
            const diff = Math.abs(ytM - igM);
            const circDist = Math.min(diff, 1440 - diff);
            if (circDist < minDist) minDist = circDist;
          }
        }
        if (minDist > maxMinDist) {
          maxMinDist = minDist;
          bestOffset = candOffset;
        }
      }

      for (let j = 0; j < ytCount; j++) {
        const totalMinutes = (j * stepYt + bestOffset) % (24 * 60);
        const h = Math.floor(totalMinutes / 60) % 24;
        const m = totalMinutes % 60;

        scheduledSlots.push({
          id: `sched_yt_${j}`,
          hour: h,
          minute: m,
          timeMinutes: totalMinutes,
          timeStr: `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`,
          account: 'youtube',
          platform: 'YouTube Shorts',
          title: `Scheduled YouTube Short ${j + 1}`,
          status: 'scheduled'
        });
      }
    }

    // Sort chronologically
    scheduledSlots.sort((a, b) => a.timeMinutes - b.timeMinutes);
  }

  // --- Calendar View Logic (Rolling 7-Day View: Today in Second Column) ---
  function getWeekRange(anchorDate) {
    // Column 0 = anchorDate - 1 day (Yesterday)
    // Column 1 = anchorDate (Today, second column)
    // Columns 2..6 = anchorDate + 1..5 days (Next 5 days)
    const base = new Date(anchorDate.getFullYear(), anchorDate.getMonth(), anchorDate.getDate(), 0, 0, 0);

    const days = [];
    for (let offset = -1; offset <= 5; offset++) {
      const d = new Date(base);
      d.setDate(base.getDate() + offset);
      days.push(d);
    }
    return days;
  }

  // --- Dynamic Multi-Lane Clustering for Overlapping Events ---
  function layoutEventsWithLanes(events) {
    events.forEach(e => {
      e.startMinutes = e.hour * 60 + (e.minute || 0);
      const durMins = Math.max(54, e.durationSec ? Math.ceil(e.durationSec / 60) : 54);
      e.endMinutes = e.startMinutes + durMins;
    });

    const sorted = [...events].sort((a, b) => a.startMinutes - b.startMinutes || (b.endMinutes - b.startMinutes) - (a.endMinutes - a.startMinutes));

    // Group overlapping events into clusters
    const clusters = [];
    let curCluster = [];
    let curEnd = -1;

    sorted.forEach(ev => {
      if (curCluster.length === 0) {
        curCluster.push(ev);
        curEnd = ev.endMinutes;
      } else if (ev.startMinutes < curEnd) {
        curCluster.push(ev);
        curEnd = Math.max(curEnd, ev.endMinutes);
      } else {
        clusters.push(curCluster);
        curCluster = [ev];
        curEnd = ev.endMinutes;
      }
    });
    if (curCluster.length > 0) {
      clusters.push(curCluster);
    }

    // Allocate lane columns in each cluster
    clusters.forEach(cluster => {
      const laneEndTimes = [];
      cluster.forEach(ev => {
        let placed = false;
        for (let l = 0; l < laneEndTimes.length; l++) {
          if (laneEndTimes[l] <= ev.startMinutes) {
            laneEndTimes[l] = ev.endMinutes;
            ev.lane = l;
            placed = true;
            break;
          }
        }
        if (!placed) {
          ev.lane = laneEndTimes.length;
          laneEndTimes.push(ev.endMinutes);
        }
      });

      const totalLanes = Math.max(1, laneEndTimes.length);
      cluster.forEach(ev => {
        ev.totalLanes = totalLanes;
      });
    });

    return sorted;
  }

  function getEventsForDate(targetDate) {
    const now = new Date();
    const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 0, 0, 0);
    const targetMidnight = new Date(targetDate.getFullYear(), targetDate.getMonth(), targetDate.getDate(), 0, 0, 0);

    const isToday = targetMidnight.getTime() === startOfToday.getTime();
    const isPast = targetMidnight.getTime() < startOfToday.getTime();
    const isFuture = targetMidnight.getTime() > startOfToday.getTime();
    const events = [];

    // 1. Posted archive clips
    postedClips.forEach(p => {
      const pDate = new Date(p.date);
      if (pDate.toDateString() === targetDate.toDateString()) {
        const acc = (p.account === 'yt') ? 'youtube' : p.account;
        events.push({
          ...p,
          account: acc,
          hour: pDate.getHours(),
          minute: pDate.getMinutes(),
          timeMinutes: pDate.getHours() * 60 + pDate.getMinutes(),
          status: 'posted'
        });
      }
    });

    // In the past: ONLY show real posted clips! Never show scheduled placeholder slots.
    if (isPast) {
      return events.sort((a, b) => a.timeMinutes - b.timeMinutes);
    }

    // 2. Today:
    if (isToday) {
      const currentMinutes = now.getHours() * 60 + now.getMinutes();

      const todayPostedCount = { ig1: 0, ig2: 0, youtube: 0 };
      const lastPostMinutes = { ig1: -9999, ig2: -9999, youtube: -9999 };

      events.forEach(e => {
        if (e.status === 'posted') {
          const acc = (e.account === 'yt') ? 'youtube' : e.account;
          todayPostedCount[acc] = (todayPostedCount[acc] || 0) + 1;
          if (e.timeMinutes > lastPostMinutes[acc]) {
            lastPostMinutes[acc] = e.timeMinutes;
          }
        }
      });

      // Filter upcoming slots that are valid:
      // - Must not have already passed in time (skip missed / late slots)
      // - Must not exceed daily limit for that account if already satisfied by real posts
      // - Must not collide with a real post within 90 minutes
      // - Must respect strict 3.0h anti-spam cooldown if account posted late
      const upcomingSlots = [];

      scheduledSlots.forEach(slot => {
        const slotMinutes = slot.hour * 60 + slot.minute;
        const acc = (slot.account === 'yt') ? 'youtube' : slot.account;
        const maxDaily = acc === 'ig1' ? settings.ig1Posts : acc === 'ig2' ? settings.ig2Posts : settings.ytPosts;

        // Skip slot if its scheduled time has already passed today
        if (slotMinutes < currentMinutes) {
          return;
        }

        // Skip if daily quota for this account is already fulfilled by real posts
        if (todayPostedCount[acc] >= maxDaily) {
          return;
        }

        // If a real post on this account happened close to this slot, suppress the slot
        const hasNearbyPost = events.some(e => e.status === 'posted' && e.account === acc && Math.abs(e.timeMinutes - slotMinutes) < 90);
        if (hasNearbyPost) {
          return;
        }

        // Strict anti-shadowban cooldown check (3.0h for Instagram, 1.0h for YouTube)
        const minGap = (acc === 'youtube') ? 60 : 180;
        if (lastPostMinutes[acc] >= 0 && slotMinutes < (lastPostMinutes[acc] + minGap)) {
          // Account posted late and is still on mandatory cooldown. Skip this slot!
          return;
        }

        upcomingSlots.push({ ...slot });
      });

      // Map priority-sorted staged pipeline clips onto the earliest upcoming slots
      sortPipelineClips();
      const activeStaged = pipelineClips.filter(c => !c.discarded);
      let stagedIdx = 0;
      upcomingSlots.forEach(slot => {
        if (stagedIdx < activeStaged.length) {
          const stagedClip = activeStaged[stagedIdx];
          events.push({
            ...stagedClip,
            account: slot.account,
            platform: slot.platform,
            hour: slot.hour,
            minute: slot.minute,
            timeMinutes: slot.hour * 60 + slot.minute,
            status: 'staged'
          });
          stagedIdx++;
        } else {
          events.push({
            ...slot,
            timeMinutes: slot.hour * 60 + slot.minute,
            date: targetDate.toISOString()
          });
        }
      });

      // Mark the immediate next upcoming event (staged or scheduled)
      const upcomingEvents = events.filter(e => e.timeMinutes >= currentMinutes);
      if (upcomingEvents.length > 0) {
        upcomingEvents.sort((a, b) => a.timeMinutes - b.timeMinutes);
        upcomingEvents[0].isNext = true;
      }
    }

    // 3. Future Days:
    if (isFuture) {
      scheduledSlots.forEach(slot => {
        events.push({
          ...slot,
          timeMinutes: slot.hour * 60 + slot.minute,
          date: targetDate.toISOString()
        });
      });
    }

    return events.sort((a, b) => a.timeMinutes - b.timeMinutes);
  }

  function matchesFilter(evt) {
    if (activeFilter === 'all') return true;
    if (activeFilter === 'staged') return evt.status === 'staged';
    const acc = (evt.account === 'yt') ? 'youtube' : evt.account;
    return acc === activeFilter;
  }

  function renderCalendar() {
    if (activeCalView === 'week') renderWeekView();
    else if (activeCalView === 'day') renderDayView();
    else if (activeCalView === 'month') renderMonthView();
  }

  function updateCurrentTimeIndicator() {
    const timeLine = document.getElementById('cal-current-time-line');
    const badge = document.getElementById('cal-current-time-badge');
    if (!timeLine) return;

    const now = new Date();
    const currentMinutes = now.getHours() * 60 + now.getMinutes();
    timeLine.style.top = `${currentMinutes}px`;
    timeLine.style.display = 'block';

    if (badge) {
      badge.innerText = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
    }
  }

  function renderWeekView() {
    const weekWrapper = document.getElementById('week-view-wrapper');
    const dayWrapper = document.getElementById('day-view-wrapper');
    const monthWrapper = document.getElementById('month-view-wrapper');

    if (weekWrapper) weekWrapper.style.display = 'flex';
    if (dayWrapper) dayWrapper.style.display = 'none';
    if (monthWrapper) monthWrapper.style.display = 'none';

    const weekDays = getWeekRange(currentDate);
    const firstDay = weekDays[0];
    const lastDay = weekDays[6];

    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const heading = document.getElementById('cal-heading');
    if (heading) {
      heading.innerText = `${months[firstDay.getMonth()]} ${firstDay.getDate()} – ${months[lastDay.getMonth()]} ${lastDay.getDate()}, ${firstDay.getFullYear()}`;
    }

    // Render Headers (Rolling 7-day: Col 0 = Yesterday, Col 1 = Today, Cols 2..6 = Next 5 days)
    const headerRow = document.getElementById('week-header-row');
    if (headerRow) {
      headerRow.innerHTML = '<div class="col-header time-label-spacer">TIME</div>';
      const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
      const todayStr = new Date().toDateString();

      weekDays.forEach(d => {
        const isToday = d.toDateString() === todayStr;
        const col = document.createElement('div');
        col.className = `col-header ${isToday ? 'today' : ''}`;
        col.innerHTML = `
          <div class="day-label">${dayNames[d.getDay()]}</div>
          <div class="day-num">${d.getDate()}</div>
        `;
        headerRow.appendChild(col);
      });
    }

    // Render Time Axis (24 Hours)
    const timeAxis = document.getElementById('time-axis-col');
    if (timeAxis) {
      timeAxis.innerHTML = '';
      for (let h = 0; h < 24; h++) {
        const slot = document.createElement('div');
        slot.className = 'time-slot-label';
        slot.innerText = `${String(h).padStart(2, '0')}:00`;
        timeAxis.appendChild(slot);
      }
    }

    // Render Day Columns with Overlapping Multi-Lane Layout & Smooth Slide
    const bodyGrid = document.getElementById('week-body-grid');
    if (bodyGrid) {
      // Trigger smooth slide transition
      bodyGrid.classList.remove('week-anim-slide');
      void bodyGrid.offsetWidth; // Force reflow
      bodyGrid.classList.add('week-anim-slide');

      const oldCols = bodyGrid.querySelectorAll('.day-column');
      oldCols.forEach(c => c.remove());

      const todayStr = new Date().toDateString();

      weekDays.forEach(d => {
        const isToday = d.toDateString() === todayStr;
        const dayCol = document.createElement('div');
        dayCol.className = `day-column ${isToday ? 'today' : ''}`;
        dayCol.dataset.date = d.toISOString().split('T')[0];

        const rawEvents = getEventsForDate(d).filter(matchesFilter);
        const dayEvents = layoutEventsWithLanes(rawEvents);

        dayEvents.forEach(evt => {
          const acc = (evt.account === 'yt') ? 'youtube' : (evt.account || 'ig1');
          const card = document.createElement('div');
          card.className = `event-card ${evt.status} account-${acc} ${evt.isNext ? 'is-next' : ''}`;
          const topPx = (evt.hour + (evt.minute || 0) / 60) * 60;
          const heightPx = Math.max(54, (evt.durationSec ? (evt.durationSec / 60) * 60 : 54));

          card.style.top = `${topPx}px`;
          card.style.height = `${heightPx}px`;

          // Handle multi-lane side-by-side positioning for overlapping cards
          if (evt.totalLanes > 1) {
            const lanePct = 100 / evt.totalLanes;
            card.classList.add('compact-lane');
            card.style.setProperty('left', `calc(${evt.lane * lanePct}% + 1px)`, 'important');
            card.style.setProperty('width', `calc(${lanePct}% - 2px)`, 'important');
            card.style.setProperty('right', 'auto', 'important');
            card.style.setProperty('z-index', `${10 + evt.lane}`);
          } else {
            card.style.setProperty('left', '3px', 'important');
            card.style.setProperty('width', 'calc(100% - 6px)', 'important');
            card.style.setProperty('right', 'auto', 'important');
            card.style.setProperty('z-index', '10');
          }

          const isCompact = evt.totalLanes > 1;
          const tagClass = acc === 'ig1' ? 'tag-ig1' : acc === 'ig2' ? 'tag-ig2' : 'tag-yt';
          const tagText = isCompact
            ? (acc === 'ig1' ? '@solvikz' : acc === 'ig2' ? '@loop' : 'YT Shorts')
            : (acc === 'ig1' ? '@solvikz' : acc === 'ig2' ? '@loopablez' : 'YouTube Shorts');
          const statusIcon = evt.status === 'posted' ? ICONS.check : evt.status === 'staged' ? ICONS.play : ICONS.clock;
          const timeStr = `${String(evt.hour).padStart(2, '0')}:${String(evt.minute || 0).padStart(2, '0')}`;

          card.title = `${evt.title} // ${acc === 'ig1' ? '@solvikz' : acc === 'ig2' ? '@loopablez' : 'YouTube Shorts'} (${timeStr})`;

          card.innerHTML = `
            <div class="event-title">
              <span class="status-icon">${statusIcon}</span>
              <span class="title-text">${evt.title}</span>
            </div>
            <div class="event-footer">
              <span class="event-account-tag ${tagClass}">${tagText}</span>
              <div class="event-footer-right">
                ${evt.isTrial ? '<span class="badge-trial">TRIAL</span>' : ''}
                ${evt.isNext ? '<span class="badge-next">NEXT</span>' : ''}
                <span class="event-time">${timeStr}</span>
              </div>
            </div>
          `;

          card.onclick = () => {
            if (evt.status === 'staged') {
              window.openPreviewModal(evt);
            } else if (evt.status === 'posted' && evt.url) {
              window.open(evt.url, '_blank');
            } else {
              alert(`Scheduled slot for ${tagText} at ${timeStr}. Will generate dynamically before publication.`);
            }
          };

          dayCol.appendChild(card);
        });

        bodyGrid.appendChild(dayCol);
      });
    }

    updateCurrentTimeIndicator();

    const scrollContainer = document.getElementById('week-scroll-container');
    const currentHour = new Date().getHours();
    if (scrollContainer && currentHour > 2) {
      scrollContainer.scrollTop = (currentHour - 2) * 60;
    }
  }

  function renderDayView() {
    const weekWrapper = document.getElementById('week-view-wrapper');
    const dayWrapper = document.getElementById('day-view-wrapper');
    const monthWrapper = document.getElementById('month-view-wrapper');

    if (weekWrapper) weekWrapper.style.display = 'none';
    if (dayWrapper) dayWrapper.style.display = 'block';
    if (monthWrapper) monthWrapper.style.display = 'none';

    const dayContainer = document.getElementById('day-view-wrapper');
    if (!dayContainer) return;
    dayContainer.innerHTML = '';

    const months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
    const heading = document.getElementById('cal-heading');
    if (heading) {
      heading.innerText = `${months[currentDate.getMonth()]} ${currentDate.getDate()}, ${currentDate.getFullYear()}`;
    }

    const events = getEventsForDate(currentDate);

    for (let h = 0; h < 24; h++) {
      const hourRow = document.createElement('div');
      hourRow.className = 'day-timeline-hour';

      const hourLabel = document.createElement('div');
      hourLabel.className = 'hour-marker';
      hourLabel.innerText = `${String(h).padStart(2, '0')}:00`;
      hourRow.appendChild(hourLabel);

      const content = document.createElement('div');
      content.className = 'hour-content';

      const hourEvents = events.filter(e => e.hour === h && matchesFilter(e));
      if (hourEvents.length === 0) {
        content.innerHTML = '<span class="empty-slot">No posts scheduled</span>';
      } else {
        hourEvents.forEach(evt => {
          const acc = (evt.account === 'yt') ? 'youtube' : (evt.account || 'ig1');
          const item = document.createElement('div');
          item.className = `event-card ${evt.status} account-${acc} ${evt.isNext ? 'is-next' : ''}`;
          item.style.position = 'static';
          item.style.height = 'auto';
          item.style.padding = '10px 14px';
          item.style.marginBottom = '6px';

          const tagClass = acc === 'ig1' ? 'tag-ig1' : acc === 'ig2' ? 'tag-ig2' : 'tag-yt';
          const tagText = acc === 'ig1' ? '@solvikz' : acc === 'ig2' ? '@loopablez' : 'YouTube Shorts';
          const statusIcon = evt.status === 'posted' ? ICONS.check : evt.status === 'staged' ? ICONS.play : ICONS.clock;
          const timeStr = `${String(evt.hour).padStart(2, '0')}:${String(evt.minute || 0).padStart(2, '0')}`;

          item.innerHTML = `
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
              <div class="event-title" style="font-size:13px;">
                <span class="status-icon">${statusIcon}</span>
                <strong class="title-text">${evt.title}</strong>
              </div>
              <div style="display:flex;align-items:center;gap:6px;">
                ${evt.isTrial ? '<span class="badge-trial">TRIAL REEL</span>' : ''}
                ${evt.isNext ? '<span class="badge-next">NEXT UP</span>' : ''}
                <span style="font-size:11px;font-family:var(--font-mono);color:var(--text-dim);">${timeStr}</span>
              </div>
            </div>
            ${evt.caption ? `<div style="font-size:11px;color:var(--text-muted);margin-bottom:6px;">${evt.caption}</div>` : ''}
            <div class="event-footer">
              <span class="event-account-tag ${tagClass}">${tagText}</span>
              <span style="font-size:10px;color:var(--text-dim);text-transform:uppercase;font-family:var(--font-mono);">${evt.status}</span>
            </div>
          `;

          item.onclick = () => {
            if (evt.status === 'staged') window.openPreviewModal(evt);
            else if (evt.status === 'posted' && evt.url) window.open(evt.url, '_blank');
            else alert(`Scheduled slot for ${tagText} at ${timeStr}. Will generate dynamically before publication.`);
          };
          content.appendChild(item);
        });
      }

      hourRow.appendChild(content);
      dayContainer.appendChild(hourRow);
    }
  }

  function renderMonthView() {
    const weekWrapper = document.getElementById('week-view-wrapper');
    const dayWrapper = document.getElementById('day-view-wrapper');
    const monthWrapper = document.getElementById('month-view-wrapper');

    if (weekWrapper) weekWrapper.style.display = 'none';
    if (dayWrapper) dayWrapper.style.display = 'none';
    if (monthWrapper) monthWrapper.style.display = 'grid';

    const monthContainer = document.getElementById('month-view-wrapper');
    if (!monthContainer) return;
    monthContainer.innerHTML = '';

    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();

    const months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
    const heading = document.getElementById('cal-heading');
    if (heading) heading.innerText = `${months[month]} ${year}`;

    const firstDayIndex = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const adjustedFirst = firstDayIndex === 0 ? 6 : firstDayIndex - 1;

    for (let i = 0; i < adjustedFirst; i++) {
      const blank = document.createElement('div');
      blank.className = 'month-cell';
      blank.style.opacity = '0.3';
      monthContainer.appendChild(blank);
    }

    const todayStr = new Date().toDateString();

    for (let d = 1; d <= daysInMonth; d++) {
      const cellDate = new Date(year, month, d);
      const isToday = cellDate.toDateString() === todayStr;

      const cell = document.createElement('div');
      cell.className = `month-cell ${isToday ? 'today' : ''}`;

      const events = getEventsForDate(cellDate).filter(matchesFilter);

      cell.innerHTML = `
        <div class="month-cell-header">
          <span>${d}</span>
          ${events.length > 0 ? `<small style="font-size:10px;color:var(--yellow);font-weight:800;">${events.length} posts</small>` : ''}
        </div>
        <div class="month-badge-strip">
          ${events.slice(0, 3).map(e => {
            const acc = (e.account === 'yt') ? 'youtube' : (e.account || 'ig1');
            const icon = e.status === 'posted' ? ICONS.check : e.status === 'staged' ? ICONS.play : ICONS.clock;
            return `
              <div class="event-card ${e.status} account-${acc}" style="position:static;padding:2px 5px;font-size:9px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-bottom:2px;">
                ${icon} ${e.isTrial ? '<span style="color:var(--yellow);font-weight:800">[TRIAL]</span> ' : ''}${e.title}
              </div>
            `;
          }).join('')}
          ${events.length > 3 ? `<div style="font-size:9px;color:var(--text-dim)">+${events.length - 3} more</div>` : ''}
        </div>
      `;

      cell.onclick = () => {
        currentDate = cellDate;
        activeCalView = 'day';
        updateViewButtons();
        renderCalendar();
      };

      monthContainer.appendChild(cell);
    }
  }

  function updateViewButtons() {
    document.querySelectorAll('.view-btn').forEach(b => {
      b.classList.toggle('active', b.dataset.calView === activeCalView);
    });
  }

  // --- Pipeline & Review Queue ---
  function renderPipelineQueue() {
    const grid = document.getElementById('pipeline-clips-grid');
    const badge = document.getElementById('pipeline-count-badge');

    // Always sort by 5-tier priority (5 down to 1) + FIFO
    sortPipelineClips();

    const activeQueue = pipelineClips.filter(c => !c.discarded);
    if (badge) badge.innerText = activeQueue.length;

    // Update priority filter pill counts: 5, 4, 3, 2, 1
    const counts = { all: activeQueue.length, '5': 0, '4': 0, '3': 0, '2': 0, '1': 0 };
    activeQueue.forEach(c => {
      const p = String(c._prio?.priority || 3);
      if (typeof counts[p] === 'number') counts[p]++;
    });
    Object.entries(counts).forEach(([k, v]) => {
      const el = document.getElementById(`prio-count-${k}`);
      if (el) el.innerText = v;
    });

    if (!grid) return;
    grid.innerHTML = '';

    const filteredClips = activePrioFilter === 'all'
      ? activeQueue
      : activeQueue.filter(c => String(c._prio?.priority || 3) === activePrioFilter);

    if (filteredClips.length === 0) {
      grid.innerHTML = `
        <div style="grid-column:1/-1;text-align:center;padding:60px 20px;border:1px dashed var(--border);border-radius:var(--radius-md);background:var(--bg-surface)">
          <div style="margin-bottom:12px;color:var(--text-dim)">${ICONS.film}</div>
          <div style="font-size:16px;font-weight:700;color:#ffffff">${activeQueue.length === 0 ? 'No Staged Clips in Pipeline' : 'No Clips in This Priority Level'}</div>
          <div style="font-size:12px;color:var(--text-muted);margin-top:4px">${activeQueue.length === 0 ? 'All harvested clips have been published. Click "Scan Live Streams" to stage new moments.' : 'Switch filter to "All" or adjust clip priority level.'}</div>
        </div>
      `;
      return;
    }

    let ig1TrialUsed = 0;
    const ig1TrialLimit = Math.max(0, safeInt(settings.ig1TrialPosts, 0));

    filteredClips.forEach(clip => {
      const queuePos = activeQueue.indexOf(clip) + 1;
      const prio = clip._prio || getClipPriority(clip);
      const isIg1 = clip.account === 'ig1' || (clip.target && clip.target.toLowerCase().includes('solvikz'));
      let isTrial = Boolean(clip.isTrial || clip.post_kind === 'trial' || clip.trial || (clip.target && clip.target.toLowerCase().includes('trial')));
      if (!isTrial && isIg1 && ig1TrialUsed < ig1TrialLimit) {
        isTrial = true;
      }
      if (isTrial && isIg1) {
        ig1TrialUsed++;
      }
      clip.isTrial = isTrial;

      const card = document.createElement('div');
      card.className = `clip-card card-${prio.tier}`;

      const tierClass = `tier-${prio.priority}`;
      const cachedBlob = clipBlobCache.get(clip.id) || clip._blobUrl;

      card.innerHTML = `
        <div class="clip-preview-container" role="button" tabindex="0" title="Click to preview video">
          <div class="clip-poster-placeholder">
            <div class="clip-play-orb">
              ${ICONS.play}
            </div>
            <div class="clip-poster-label">${clip.streamer || 'Streamer'}</div>
          </div>
          ${cachedBlob ? `<video src="${cachedBlob}" preload="none" muted playsinline></video>` : ''}
          <div class="clip-overlay-badge">
            <span>${clip.streamer}</span>
          </div>
          <div class="clip-rank-badge ${queuePos === 1 ? 'is-first' : ''}">
            ${queuePos === 1 ? '#1 NEXT UP' : '#' + queuePos}
          </div>
          ${isTrial ? '<div style="position:absolute;bottom:8px;left:8px;z-index:4;"><span class="clip-trial-tag">TRIAL REEL</span></div>' : ''}
          <div class="clip-duration-badge" style="z-index:4;">${clip.duration}</div>
        </div>
        <div class="clip-body">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:6px;flex-wrap:wrap;">
            <div class="clip-title" style="flex:1;min-width:140px;">${clip.title}</div>
            <span class="prio-tier-badge ${tierClass}">${prio.label}</span>
          </div>
          <div style="display:flex;gap:6px;flex-wrap:wrap;align-items:center;">
            ${clip.game ? `<span class="clip-game-tag">${clip.game}</span>` : ''}
            ${clip.smart_edited ? '<span class="clip-smart-edit-tag">⏩ SMART EDITED</span>' : ''}
            ${clip.nsfw_censored ? '<span class="clip-censored-tag">AUTO-CENSORED</span>' : ''}
            ${isTrial ? '<span class="clip-trial-tag">TRIAL REEL</span>' : ''}
          </div>
          <div class="clip-caption">${clip.caption}</div>
          <div class="clip-metrics">
            <span>Spike: ${clip.sigma}</span> • 
            <span>${clip.post_to_yt ? '<strong style="color:#ffffff">IG + YouTube</strong>' : '<span style="color:var(--text-muted)">Instagram Only</span>'}</span>
          </div>
        </div>
        <div class="clip-prio-bar">
          <span style="font-size:10px;font-family:var(--font-mono);color:var(--text-dim);align-self:center;margin-right:2px;">PRIO:</span>
          <button class="btn btn-sm ${prio.priority === 5 ? 'btn-yellow' : ''}" style="flex:1;padding:2px 0;" onclick="window.setPriorityDirect('${clip.id}', 5)" title="P5 (Highest)">5</button>
          <button class="btn btn-sm ${prio.priority === 4 ? 'btn-yellow' : ''}" style="flex:1;padding:2px 0;" onclick="window.setPriorityDirect('${clip.id}', 4)" title="P4 (Prioritized)">4</button>
          <button class="btn btn-sm ${prio.priority === 3 ? 'btn-yellow' : ''}" style="flex:1;padding:2px 0;" onclick="window.setPriorityDirect('${clip.id}', 3)" title="P3 (Default)">3</button>
          <button class="btn btn-sm ${prio.priority === 2 ? 'btn-yellow' : ''}" style="flex:1;padding:2px 0;" onclick="window.setPriorityDirect('${clip.id}', 2)" title="P2 (Unprioritized)">2</button>
          <button class="btn btn-sm ${prio.priority === 1 ? 'btn-yellow' : ''}" style="flex:1;padding:2px 0;" onclick="window.setPriorityDirect('${clip.id}', 1)" title="P1 (Lowest)">1</button>
        </div>
        <div class="clip-actions">
          <button class="btn btn-yellow btn-sm btn-preview" style="flex:2;justify-content:center">Preview</button>
          <button class="btn btn-warning btn-sm btn-discard" style="flex:1;justify-content:center" title="Discard clip (6h timer before automated deletion)">🗑️ Discard</button>
        </div>
      `;

      const prevBox = card.querySelector('.clip-preview-container');
      if (prevBox) {
        prevBox.onclick = () => window.openPreviewModal(clip);
        prevBox.onkeydown = (e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            window.openPreviewModal(clip);
          }
        };
      }

      card.querySelector('.btn-preview').onclick = () => window.openPreviewModal(clip);
      card.querySelector('.btn-discard').onclick = () => discardClip(clip, false);

      grid.appendChild(card);
    });
  }

  // --- Discarded Clips Queue (6-Hour Deletion Window) ---
  function renderDiscardedQueue() {
    const grid = document.getElementById('discarded-clips-grid');
    const badge = document.getElementById('discarded-count-badge');
    const discardedClips = pipelineClips.filter(c => Boolean(c.discarded));

    if (badge) {
      badge.innerText = discardedClips.length;
      badge.style.display = discardedClips.length > 0 ? 'inline-block' : 'none';
    }

    if (!grid) return;
    grid.innerHTML = '';

    if (discardedClips.length === 0) {
      grid.innerHTML = `
        <div style="grid-column:1/-1;text-align:center;padding:60px 20px;border:1px dashed var(--border);border-radius:var(--radius-md);background:var(--bg-surface)">
          <div style="margin-bottom:12px;color:var(--text-dim)">
            <svg class="icon icon-lg" viewBox="0 0 24 24" style="width:36px;height:36px;"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
          </div>
          <div style="font-size:16px;font-weight:700;color:#ffffff">No Discarded Clips</div>
          <div style="font-size:12px;color:var(--text-muted);margin-top:4px;max-width:440px;margin-left:auto;margin-right:auto">
            Clips marked with issues or discarded from publishing will appear here. They are held for <strong>6 hours</strong> before automated permanent deletion.
          </div>
        </div>
      `;
      return;
    }

    discardedClips.forEach(clip => {
      const discAt = clip.discarded_at ? new Date(clip.discarded_at).getTime() : Date.now();
      const expiresAt = discAt + (6 * 3600 * 1000);
      const remainingMs = expiresAt - Date.now();

      let timerText = '';
      let timerClass = 'discard-timer-badge';
      if (remainingMs <= 0) {
        timerText = '⚠️ Expired (>6h) - Ready to Purge';
        timerClass += ' expired';
      } else {
        const hrs = Math.floor(remainingMs / (3600 * 1000));
        const mins = Math.floor((remainingMs % (3600 * 1000)) / (60 * 1000));
        timerText = `⏰ Deletes in ${hrs}h ${mins}m`;
        if (hrs < 1) timerClass += ' urgent';
      }

      const origPrio = clip.pre_discard_priority || 3;
      const streamer = clip.streamer || clip.username || 'Streamer';
      const game = clip.game || 'Game';
      const dur = clip.duration || (clip.duration_sec ? `${Math.round(clip.duration_sec)}s` : '30s');

      const card = document.createElement('div');
      card.className = 'clip-card discard-card';
      card.innerHTML = `
        <div class="clip-preview-wrap" style="position:relative;background:#000;aspect-ratio:9/16;max-height:280px;display:flex;align-items:center;justify-content:center;overflow:hidden;">
          ${clip.videoUrl ? `<video src="${clip.videoUrl}" style="width:100%;height:100%;object-fit:cover;" preload="none" muted playsinline></video>` : `<div class="text-muted font-mono" style="font-size:12px;">Video Staged</div>`}
          <span class="${timerClass}" style="position:absolute;top:8px;left:8px;z-index:2;">${timerText}</span>
          <span class="prio-tier-badge tier-${origPrio}" style="position:absolute;top:8px;right:8px;z-index:2;">Prior: P${origPrio}</span>
        </div>
        <div class="clip-body" style="padding:12px;">
          <div style="font-weight:700;font-size:13px;line-height:1.3;margin-bottom:6px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${clip.title}">${clip.title}</div>
          <div style="display:flex;align-items:center;gap:6px;font-size:11px;color:var(--text-muted);margin-bottom:8px;">
            <span>${streamer}</span> • <span>${game}</span> • <span>${dur}</span>
          </div>
          <div class="clip-caption" style="font-size:11px;max-height:38px;overflow:hidden;color:var(--text-dim);">${clip.caption || ''}</div>
        </div>
        <div class="discard-actions">
          <button class="btn btn-sm btn-outline btn-restore" style="flex:1;justify-content:center;">
            <svg class="icon" viewBox="0 0 24 24"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/></svg>
            Restore
          </button>
          <button class="btn btn-sm btn-danger btn-delete-perm" style="flex:1;justify-content:center;">
            <svg class="icon" viewBox="0 0 24 24"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
            Delete Permanently
          </button>
        </div>
      `;

      const previewWrap = card.querySelector('.clip-preview-wrap');
      if (previewWrap) {
        previewWrap.style.cursor = 'pointer';
        previewWrap.onclick = () => window.openPreviewModal(clip);
      }

      card.querySelector('.btn-restore').onclick = (e) => {
        e.stopPropagation();
        restoreClip(clip);
      };
      card.querySelector('.btn-delete-perm').onclick = (e) => {
        e.stopPropagation();
        deletePermanently(clip);
      };

      grid.appendChild(card);
    });
  }

  // --- Modal Controllers (Exposed Globally) ---
  window.openSetupModal = function () {
    const modal = document.getElementById('modal-setup');
    if (!modal) return;
    const patEl = document.getElementById('setup-pat');
    const repoEl = document.getElementById('setup-repo');
    const branchEl = document.getElementById('setup-branch');
    const contentBranchEl = document.getElementById('setup-content-branch');

    if (patEl) patEl.value = auth.pat || '';
    if (repoEl) repoEl.value = auth.repo || 'Deeptanil/HyperClip-AI';
    if (branchEl) branchEl.value = auth.branch || 'master';
    if (contentBranchEl) contentBranchEl.value = auth.contentBranch || 'content';

    modal.classList.add('open');
  };

  window.closeSetupModal = function () {
    const modal = document.getElementById('modal-setup');
    if (modal) modal.classList.remove('open');
  };

  let activePreviewSessionId = 0;

  window.openPreviewModal = async function (clip) {
    const currentSession = ++activePreviewSessionId;
    selectedClip = clip;
    isPreviewModalActive = true;

    // Abort any previous pending blob download to save bandwidth and memory
    if (activePreviewAbortController) {
      activePreviewAbortController.abort();
    }
    activePreviewAbortController = new AbortController();
    const abortSignal = activePreviewAbortController.signal;

    const modal = document.getElementById('modal-preview');
    const player = document.getElementById('preview-player');
    if (!modal || !player) return;

    // Immediately stop old video, detach error listeners, blank video surface, and show loader
    player.pause();
    player.onerror = null;
    player.oncanplay = null;
    player.onloadeddata = null;
    player.removeAttribute('src');
    player.load();
    player.style.opacity = '0';

    const loader = document.getElementById('preview-video-loader');
    const errorEl = document.getElementById('preview-video-error');
    if (loader) loader.style.display = 'flex';
    if (errorEl) errorEl.style.display = 'none';

    const badge = document.getElementById('preview-streamer-badge');
    const title = document.getElementById('preview-modal-title');
    const titleEdit = document.getElementById('preview-title-edit');
    const caption = document.getElementById('preview-caption-edit');
    const gameEl = document.getElementById('preview-game');
    const prioValEl = document.getElementById('preview-priority-val');
    const sigma = document.getElementById('preview-sigma');
    const motion = document.getElementById('preview-motion');
    const layout = document.getElementById('preview-layout');
    const target = document.getElementById('preview-target');

    const effPrio = getClipPriority(clip);
    if (badge) badge.innerText = `${clip.streamer} // Highlight`;
    if (title) title.innerText = clip.title;
    if (titleEdit) titleEdit.value = clip.title || '';
    if (caption) caption.value = clip.caption || '';
    if (gameEl) gameEl.innerText = clip.game || 'Uncategorized';
    if (prioValEl) prioValEl.innerHTML = `<span class="prio-tier-badge tier-${effPrio.priority}">${effPrio.label}</span>`;
    if (sigma) sigma.innerText = clip.sigma || '3.5 σ';
    if (motion) motion.innerText = clip.motion || 'High Action Active';
    if (layout) layout.innerText = clip.layout || 'Dual Stack 9:16';
    if (target) target.innerText = clip.target || 'Instagram & YouTube';

    document.querySelectorAll('#preview-priority-controls .prio-select-btn').forEach(btn => {
      btn.classList.toggle('active', parseInt(btn.dataset.setPriority, 10) === effPrio.priority);
    });

    const trialPill = document.getElementById('preview-trial-pill');
    const postFormat = document.getElementById('preview-post-format');
    const smartPacingEl = document.getElementById('preview-smart-edit');
    if (smartPacingEl) {
      smartPacingEl.innerHTML = clip.smart_edited
        ? '<span style="color:#38bdf8;font-weight:700">⏩ Fast-Forwarded Dead Air (3x)</span>'
        : '<span style="color:var(--text-muted)">Original 1x Tempo</span>';
    }
    if (trialPill) {
      trialPill.style.display = clip.isTrial ? 'inline-flex' : 'none';
    }
    if (postFormat) {
      postFormat.innerHTML = clip.isTrial 
        ? '<span class="clip-trial-tag" style="margin-right:4px;">TRIAL REEL</span> Tests reach with non-followers'
        : 'Standard Feed Reel (Followers & Explore)';
    }

    modal.classList.add('open');

    // Retrieve from memory cache if available
    if (clipBlobCache.has(clip.id)) {
      clip._blobUrl = clipBlobCache.get(clip.id);
    }

    // Secure streaming loader: If authenticated to GitHub, stream binary via Blob URL
    // This allows private repository MP4s to play seamlessly in HTML5 <video> without auth blocks!
    if (auth.pat && !auth.isDemo && clip.path && !clip._blobUrl) {
      try {
        const res = await fetch(`https://api.github.com/repos/${auth.repo}/contents/${clip.path}?ref=${auth.contentBranch || 'content'}`, {
          headers: {
            'Authorization': `token ${auth.pat.trim()}`,
            'Accept': 'application/vnd.github.v3.raw'
          },
          signal: abortSignal
        });
        if (currentSession !== activePreviewSessionId) return;
        if (res.ok) {
          const blob = await res.blob();
          if (currentSession !== activePreviewSessionId) return;
          const newBlobUrl = URL.createObjectURL(blob);
          clip._blobUrl = newBlobUrl;
          // Maintain a bounded LRU cache (max 3 items) to avoid device memory bloat
          if (clipBlobCache.size >= 3) {
            const oldestKey = clipBlobCache.keys().next().value;
            const oldUrl = clipBlobCache.get(oldestKey);
            clipBlobCache.delete(oldestKey);
            try { URL.revokeObjectURL(oldUrl); } catch (e) {}
          }
          clipBlobCache.set(clip.id, newBlobUrl);
        }
      } catch (err) {
        if (err.name !== 'AbortError') {
          console.warn('Blob stream fallback to direct URL:', err);
        }
      }
    }

    if (currentSession !== activePreviewSessionId) return;

    // Build candidate source list with local and remote fallbacks
    const candidates = [];
    if (clip._blobUrl) candidates.push(clip._blobUrl);
    if (clip.filename && (auth.isDemo || !auth.pat)) {
      candidates.push(`media/${clip.filename}`);
    }
    if (clip.videoUrl && !clip.videoUrl.includes('raw.githubusercontent.com')) {
      candidates.push(clip.videoUrl);
    }

    let candidateIdx = 0;
    function loadNextSource() {
      if (currentSession !== activePreviewSessionId) return;
      if (candidateIdx >= candidates.length) {
        console.warn('All playback sources exhausted for clip:', clip.title);
        const lEl = document.getElementById('preview-video-loader');
        const errEl = document.getElementById('preview-video-error');
        if (lEl) lEl.style.display = 'none';
        if (errEl) errEl.style.display = 'flex';
        player.style.opacity = '0';
        return;
      }
      const nextSrc = candidates[candidateIdx++];
      player.src = nextSrc;
      player.load();
      player.play().catch(() => {});
    }

    player.oncanplay = function () {
      if (currentSession !== activePreviewSessionId) return;
      const lEl = document.getElementById('preview-video-loader');
      const errEl = document.getElementById('preview-video-error');
      if (lEl) lEl.style.display = 'none';
      if (errEl) errEl.style.display = 'none';
      player.style.opacity = '1';
    };

    player.onerror = function () {
      if (currentSession !== activePreviewSessionId) return;
      console.warn('Source playback failed, falling back to next candidate:', player.src);
      loadNextSource();
    };

    loadNextSource();
  };

  window.closePreviewModal = function () {
    activePreviewSessionId++; // Invalidate any running session
    isPreviewModalActive = false;
    if (activePreviewAbortController) {
      activePreviewAbortController.abort();
      activePreviewAbortController = null;
    }
    const modal = document.getElementById('modal-preview');
    const player = document.getElementById('preview-player');
    if (player) {
      player.pause();
      player.onerror = null;
      player.oncanplay = null;
      player.onloadeddata = null;
      player.removeAttribute('src');
      player.load();
      player.style.opacity = '0';
    }
    const loader = document.getElementById('preview-video-loader');
    const errorEl = document.getElementById('preview-video-error');
    if (loader) loader.style.display = 'none';
    if (errorEl) errorEl.style.display = 'none';
    const titleEdit = document.getElementById('preview-title-edit');
    if (titleEdit) titleEdit.value = '';
    const captionEl = document.getElementById('preview-caption-edit');
    if (captionEl) captionEl.value = '';
    if (modal) modal.classList.remove('open');
    selectedClip = null;

    // Apply any deferred queue and calendar update that completed while preview was open
    if (pendingRenderAfterModal) {
      pendingRenderAfterModal = false;
      calculateDynamicSpacing();
      renderCalendar();
      renderPipelineQueue();
    }
  };

  async function updateGitHubClipMetadata(clip, updates) {
    if (!auth.pat || auth.isDemo) return false;
    try {
      const headers = {
        'Authorization': `token ${auth.pat.trim()}`,
        'Accept': 'application/vnd.github.v3+json'
      };
      const cBranch = auth.contentBranch || 'content';
      const targetPath = clip.jsonPath || (clip.path ? clip.path.replace(/\.mp4$/i, '.json') : `output/stream_pipeline/${clip.filename.replace(/\.mp4$/i, '.json')}`);

      const getRes = await fetch(`https://api.github.com/repos/${auth.repo}/contents/${targetPath}?ref=${cBranch}`, { headers });
      if (!getRes.ok) return false;
      const getData = await getRes.json();
      const currentContent = JSON.parse(decodeURIComponent(escape(atob(getData.content))));

      const merged = { ...currentContent, ...updates };
      const newBase64 = btoa(unescape(encodeURIComponent(JSON.stringify(merged, null, 2))));

      const putRes = await fetch(`https://api.github.com/repos/${auth.repo}/contents/${targetPath}`, {
        method: 'PUT',
        headers,
        body: JSON.stringify({
          message: `chore: update clip metadata (${updates.priority ? 'prio ' + updates.priority : (updates.discarded ? 'discarded' : 'updated')}) for ${clip.filename}`,
          content: newBase64,
          sha: getData.sha,
          branch: cBranch
        })
      });
      if (putRes.ok) {
        const putData = await putRes.json();
        clip.jsonSha = putData.content.sha;
        clip.jsonPath = targetPath;
        metadataCacheBySha.set(putData.content.sha, merged);
        metadataCacheBySha.set(getData.sha, merged);
        return true;
      } else {
        const errBody = await putRes.json().catch(() => ({}));
        console.warn('GitHub clip metadata PUT failed:', putRes.status, errBody);
        return false;
      }
    } catch (e) {
      console.warn('Failed to update GitHub clip metadata:', e);
      return false;
    }
  }

  async function setClipPriority(clip, newPrio, isFromModal = false) {
    if (!clip) return;
    const p = parseInt(newPrio, 10);
    clip.priority = (p >= 1 && p <= 5) ? p : 3;

    let newTitle = clip.title;
    let newCaption = clip.caption;
    if (isFromModal && selectedClip && selectedClip.id === clip.id) {
      const titleEl = document.getElementById('preview-title-edit');
      if (titleEl && titleEl.value.trim()) {
        newTitle = titleEl.value.trim();
      }
      const captionEl = document.getElementById('preview-caption-edit');
      if (captionEl && captionEl.value.trim()) {
        newCaption = captionEl.value.trim();
      }
    }
    clip.title = newTitle;
    clip.caption = newCaption;

    // Immediately persist override to localStorage so it never reverts
    saveLocalOverride(clip, {
      title: clip.title,
      priority: clip.priority,
      caption: newCaption
    });

    sortPipelineClips();
    renderPipelineQueue();
    renderDiscardedQueue();
    renderCalendar();

    if (isFromModal && selectedClip && selectedClip.id === clip.id) {
      const modalTitle = document.getElementById('preview-modal-title');
      if (modalTitle) modalTitle.innerText = clip.title;
      const effPrio = getClipPriority(clip);
      const prioValEl = document.getElementById('preview-priority-val');
      if (prioValEl) prioValEl.innerHTML = `<span class="prio-tier-badge tier-${effPrio.priority}">${effPrio.label}</span>`;
      document.querySelectorAll('#preview-priority-controls .prio-select-btn').forEach(btn => {
        btn.classList.toggle('active', parseInt(btn.dataset.setPriority, 10) === effPrio.priority);
      });
    }

    // Auto-sync in background to repository
    updateGitHubClipMetadata(clip, {
      title: clip.title,
      priority: clip.priority,
      caption: newCaption
    }).then(ok => {
      if (ok) syncWithGitHub(false);
    });
  }

  async function discardClip(clip, isFromModal = false) {
    if (!clip) return;
    const nowIso = new Date().toISOString();
    const currentPrio = clip._prio ? clip._prio.priority : (clip.priority || 3);

    clip.discarded = true;
    clip.discarded_at = nowIso;
    clip.pre_discard_priority = currentPrio;

    // Immediately persist to localStorage so it NEVER reverts on reload or sync
    saveLocalOverride(clip, {
      discarded: true,
      discarded_at: nowIso,
      pre_discard_priority: currentPrio
    });

    sortPipelineClips();
    renderPipelineQueue();
    renderDiscardedQueue();
    renderCalendar();

    if (isFromModal) {
      window.closePreviewModal();
    }

    // Auto-sync in background to repository
    updateGitHubClipMetadata(clip, {
      discarded: true,
      discarded_at: nowIso,
      pre_discard_priority: currentPrio
    }).then(ok => {
      if (ok) syncWithGitHub(false);
    });
  }

  async function restoreClip(clip) {
    if (!clip) return;
    const restoredPrio = clip.pre_discard_priority || 3;
    clip.discarded = false;
    clip.priority = restoredPrio;
    delete clip.discarded_at;
    delete clip.pre_discard_priority;

    // Persist restored status
    saveLocalOverride(clip, {
      discarded: false,
      discarded_at: null,
      pre_discard_priority: null,
      priority: restoredPrio
    });

    sortPipelineClips();
    renderPipelineQueue();
    renderDiscardedQueue();
    renderCalendar();

    // Auto-sync in background
    updateGitHubClipMetadata(clip, {
      discarded: false,
      priority: restoredPrio,
      discarded_at: null,
      pre_discard_priority: null
    }).then(ok => {
      if (ok) syncWithGitHub(false);
    });
  }

  async function deletePermanently(clip) {
    if (!clip) return;
    const confirmed = confirm(`Are you sure you want to permanently delete "${clip.title}"?\n\nThis will immediately remove both the video and metadata files. This action cannot be undone.`);
    if (!confirmed) return;

    saveLocalOverride(clip, { permanently_deleted: true });

    if (auth.pat && !auth.isDemo && clip.path && clip.sha) {
      try {
        const headers = {
          'Authorization': `token ${auth.pat.trim()}`,
          'Accept': 'application/vnd.github.v3+json'
        };
        const cBranch = auth.contentBranch || 'content';

        // Delete MP4 from GitHub
        await fetch(`https://api.github.com/repos/${auth.repo}/contents/${clip.path}`, {
          method: 'DELETE',
          headers,
          body: JSON.stringify({
            message: `chore: purge clip ${clip.filename} via dashboard`,
            sha: clip.sha,
            branch: cBranch
          })
        });

        // Delete matching JSON if exists
        const jsonPath = clip.jsonPath || (clip.path ? clip.path.replace(/\.mp4$/i, '.json') : `output/stream_pipeline/${clip.filename.replace(/\.mp4$/i, '.json')}`);
        if (clip.jsonSha) {
          await fetch(`https://api.github.com/repos/${auth.repo}/contents/${jsonPath}`, {
            method: 'DELETE',
            headers,
            body: JSON.stringify({
              message: `chore: purge metadata for ${clip.filename} via dashboard`,
              sha: clip.jsonSha,
              branch: cBranch
            })
          });
        }
      } catch (e) {
        console.warn('GitHub remote file deletion error:', e);
      }
    }

    pipelineClips = pipelineClips.filter(c => c.id !== clip.id);
    sortPipelineClips();
    renderPipelineQueue();
    renderDiscardedQueue();
    renderCalendar();
    window.closePreviewModal();
  }

  async function purgeExpiredDiscarded() {
    const expired = pipelineClips.filter(c => {
      if (!c.discarded || !c.discarded_at) return false;
      const ageMs = Date.now() - new Date(c.discarded_at).getTime();
      return ageMs >= (6 * 3600 * 1000);
    });

    if (expired.length === 0) {
      alert('No discarded clips have exceeded the 6-hour deletion window yet.');
      return;
    }

    const confirmed = confirm(`Found ${expired.length} discarded clip(s) older than 6 hours. Permanently delete them now?`);
    if (!confirmed) return;

    for (const c of expired) {
      await deletePermanently(c);
    }
  }

  window.setPriorityDirect = function(id, p) {
    const c = pipelineClips.find(x => x.id === id);
    if (c) setClipPriority(c, p, false);
  };

  window.restoreClipById = function(id) {
    const c = pipelineClips.find(x => x.id === id);
    if (c) restoreClip(c);
  };

  window.deletePermanentlyById = function(id) {
    const c = pipelineClips.find(x => x.id === id);
    if (c) deletePermanently(c);
  };

  // --- Real GitHub REST API Integration & Data Engine ---
  let isSyncing = false;
  let lastSyncDate = null;

  async function syncWithGitHub(isManual = false) {
    if (isSyncing) return;
    isSyncing = true;

    const btnSync = document.getElementById('btn-sync');
    const syncIcon = btnSync ? btnSync.querySelector('.icon') : null;
    if (syncIcon) syncIcon.classList.add('spin-icon');

    const statusText = document.getElementById('conn-status-text');
    const dot = document.getElementById('conn-dot');

    if (!auth.pat || auth.isDemo) {
      if (dot) dot.className = 'dot yellow';
      if (statusText) statusText.innerText = 'Demo';
      const pill = document.getElementById('conn-status-pill');
      if (pill) pill.title = 'Demo Mode (Read-Only) • Connect GitHub PAT in Setup';
      loadDemoData();
      isSyncing = false;
      if (syncIcon) syncIcon.classList.remove('spin-icon');
      return;
    }

    try {
      if (statusText && isManual) statusText.innerText = 'Syncing...';
      if (dot && isManual) dot.className = 'dot yellow';

      const cleanPat = auth.pat.trim();
      const headers = {
        'Authorization': `token ${cleanPat}`,
        'Accept': 'application/vnd.github.v3+json'
      };

      // 1. Verify Repository Access
      const repoRes = await fetch(`https://api.github.com/repos/${auth.repo}`, { headers });
      if (!repoRes.ok) {
        const errJson = await repoRes.json().catch(() => ({}));
        throw new Error(errJson.message || `Repository access failed (${repoRes.status})`);
      }

      // 2. Fetch config.json from production branch (master)
      const pBranch = auth.branch || 'master';
      const configRes = await fetch(`https://api.github.com/repos/${auth.repo}/contents/config.json?ref=${pBranch}&_t=${Date.now()}`, {
        headers: { ...headers, 'Cache-Control': 'no-cache, no-store, must-revalidate', 'Pragma': 'no-cache' }
      });
      if (configRes.ok) {
        const configData = await configRes.json();
        const contentStr = decodeURIComponent(escape(atob(configData.content)));
        const configJson = JSON.parse(contentStr);
        applyRemoteConfig(configJson);
      }

      // 3. Fetch Real Posted Audit Logs from Content Branch
      const cBranch = auth.contentBranch || 'content';
      let realPosted = [];
      let totalMediaBytes = 0;

      // Try posted_twitch_log.json on content branch, fallback to master
      for (const branchAttempt of [cBranch, pBranch]) {
        try {
          const logRes = await fetch(`https://api.github.com/repos/${auth.repo}/contents/posted_twitch_log.json?ref=${branchAttempt}`, { headers });
          if (logRes.ok) {
            const logData = await logRes.json();
            const logStr = decodeURIComponent(escape(atob(logData.content)));
            const logEntries = JSON.parse(logStr);
            if (Array.isArray(logEntries)) {
              logEntries.forEach((entry, idx) => {
                const uploads = entry.uploads || {};
                const clips = entry.clips_used || [];
                const clipMap = entry.upload_clip_map || {};
                const captionsMap = entry.upload_captions || {};

                for (const [k, v] of Object.entries(uploads)) {
                  if (typeof v === 'string' && !v.toLowerCase().startsWith('failed')) {
                    const isIg1 = k.includes('instagram_1');
                    const isIg2 = k.includes('instagram_2') || (!isIg1 && k.includes('instagram'));
                    const isYt = k.includes('youtube');

                    let cname = 'Published Clip';
                    if (clipMap[k]) {
                      cname = clipMap[k];
                    } else if (clips.length === 1) {
                      cname = clips[0];
                    } else if (clips.length > 1) {
                      if (isYt) {
                        cname = clips[0];
                      } else if (isIg1 || isIg2) {
                        cname = clips[1] || clips[0];
                      }
                    }

                    const cleanTitle = cname.replace('.mp4', '').replace(/^\d{4}-\d{2}-\d{2}-/, '').replace(/_/g, ' ');

                    realPosted.push({
                      id: `posted_${idx}_${k}`,
                      title: cleanTitle.charAt(0).toUpperCase() + cleanTitle.slice(1),
                      caption: captionsMap[k] || '',
                      account: isIg1 ? 'ig1' : isIg2 ? 'ig2' : 'youtube',
                      platform: isIg1 ? 'Instagram (@solvikz)' : isIg2 ? 'Instagram (@loopablez)' : 'YouTube Shorts',
                      date: entry.timestamp,
                      timestamp: entry.timestamp,
                      url: v,
                      status: 'posted',
                      cname: cname
                    });
                  }
                }
              });
            }
            if (realPosted.length > 0) break;
          }
        } catch (e) {
          console.warn('posted_twitch_log read attempt error:', e);
        }
      }

      // 4. Fetch Real Staged Pipeline Clips from Content Branch
      let realPipeline = [];
      const pipelineCandidates = [
        'output/stream_pipeline',
        'output/twitch_pipeline'
      ];

      for (const folder of pipelineCandidates) {
        try {
          const folderRes = await fetch(`https://api.github.com/repos/${auth.repo}/contents/${folder}?ref=${cBranch}`, { headers });
          if (folderRes.ok) {
            const files = await folderRes.json();
            if (Array.isArray(files)) {
              const mp4s = files.filter(f => f.name.endsWith('.mp4'));
              const jsons = files.filter(f => f.name.endsWith('.json'));

              for (const mp4 of mp4s) {
                totalMediaBytes += (mp4.size || 0);
                const baseName = mp4.name.replace('.mp4', '');
                const jsonFile = jsons.find(j => j.name === `${baseName}.json`);

                let meta = {
                  title: baseName.replace(/^\d{4}-\d{2}-\d{2}-/, '').replace(/_/g, ' '),
                  caption: `#gaming #shorts #reels`,
                  streamer: 'Streamer',
                  z_score: 3.2,
                  hype_score: 150
                };

                let jsonSha = null;
                if (jsonFile) {
                  totalMediaBytes += (jsonFile.size || 0);
                  jsonSha = jsonFile.sha;
                  if (metadataCacheBySha.has(jsonSha)) {
                    meta = { ...meta, ...metadataCacheBySha.get(jsonSha) };
                  } else {
                    try {
                      const mRes = await fetch(jsonFile.url, { headers });
                      if (mRes.ok) {
                        const mData = await mRes.json();
                        const mStr = decodeURIComponent(escape(atob(mData.content)));
                        const parsedMeta = JSON.parse(mStr);
                        meta = { ...meta, ...parsedMeta };
                        metadataCacheBySha.set(jsonSha, parsedMeta);
                      }
                    } catch (e) {
                      console.warn('Metadata fetch error for', jsonFile.name, e);
                    }
                  }
                }

                // Raw GitHub URL for video playback
                const rawVideoUrl = mp4.download_url || `https://raw.githubusercontent.com/${auth.repo}/${cBranch}/${mp4.path}`;

                const isTrial = Boolean(
                  meta.trial ||
                  meta.is_trial ||
                  meta.post_kind === 'trial' ||
                  (meta.target && meta.target.toLowerCase().includes('trial'))
                );

                const durSec = meta.duration_sec || 35;
                const durMinStr = `${Math.floor(durSec / 60)}:${String(durSec % 60).padStart(2, '0')}`;

                let assignedAcc = 'ig1';
                if (meta.account) {
                  assignedAcc = meta.account === 'yt' ? 'youtube' : meta.account;
                } else if (meta.target) {
                  const tLower = meta.target.toLowerCase();
                  if (tLower.includes('loopablez') || tLower.includes('slot 2')) assignedAcc = 'ig2';
                  else if (tLower.includes('solvikz') || tLower.includes('slot 1')) assignedAcc = 'ig1';
                  else if (tLower.includes('youtube') || tLower.includes('shorts')) assignedAcc = 'youtube';
                }

                realPipeline.push({
                  id: `real_${baseName}`,
                  filename: mp4.name,
                  streamer: meta.streamer || meta.username || 'Stream Highlight',
                  game: meta.game || meta.category || '',
                  category: meta.category || meta.game || '',
                  title: meta.title || baseName.replace(/_/g, ' '),
                  caption: meta.caption || `${meta.title} #gaming #reels`,
                  duration: durMinStr,
                  durationSec: durSec,
                  sigma: meta.z_score ? `${Number(meta.z_score).toFixed(1)} σ` : '3.2 σ',
                  motion: 'Active Motion Detected',
                  layout: meta.layout || 'Dual Stack 9:16',
                  target: meta.target || (meta.post_to_yt ? 'Instagram & YouTube' : 'Instagram Only'),
                  post_to_yt: Boolean(meta.post_to_yt || (meta.target && meta.target.toLowerCase().includes('youtube'))),
                  posted_to_instagram: Boolean(meta.posted_to_instagram),
                  posted_to_youtube: Boolean(meta.posted_to_youtube),
                  account: assignedAcc,
                  isTrial: isTrial,
                  status: 'staged',
                  priority: meta.priority ?? 3,
                  discarded: Boolean(meta.discarded),
                  discarded_at: meta.discarded_at || null,
                  pre_discard_priority: meta.pre_discard_priority || null,
                  smart_edited: Boolean(meta.smart_edited || (Array.isArray(meta.fast_forward_segments) && meta.fast_forward_segments.length > 0)),
                  fast_forward_segments: Array.isArray(meta.fast_forward_segments) ? meta.fast_forward_segments : [],
                  nsfw_censored: Boolean(meta.nsfw_censored),
                  nsfw_segments: Array.isArray(meta.nsfw_segments) ? meta.nsfw_segments : [],
                  timestamp: meta.timestamp || meta.staged_at || meta.created_at || null,
                  videoUrl: rawVideoUrl,
                  path: mp4.path,
                  sha: mp4.sha,
                  jsonPath: jsonFile ? jsonFile.path : null,
                  jsonSha: jsonSha
                });
              }
            }
          }
          if (realPipeline.length > 0) break;
        } catch (e) {
          console.warn('Pipeline folder fetch error for', folder, e);
        }
      }

      // 5. Query Posted Archive Folders for Real Storage Size
      const postedCandidates = ['output/stream_posted', 'output/twitch_posted'];
      for (const pFolder of postedCandidates) {
        try {
          const pRes = await fetch(`https://api.github.com/repos/${auth.repo}/contents/${pFolder}?ref=${cBranch}`, { headers });
          if (pRes.ok) {
            const pFiles = await pRes.json();
            if (Array.isArray(pFiles)) {
              pFiles.forEach(f => { totalMediaBytes += (f.size || 0); });
            }
          }
        } catch (e) {}
      }

      // 6. Apply persistent local overrides (so discarded status & custom priorities never revert)
      realPipeline.forEach(c => applyOverridesToClip(c));
      realPipeline = realPipeline.filter(c => !c._deleted);

      // Bind Real Data to Dashboard State & Sort by 5-Tier Priority + FIFO
      pipelineClips = realPipeline;
      postedClips = realPosted;
      sortPipelineClips();

      // Update real top stats from actual posted data (matching local/UTC day or rolling 24h window)
      const now = new Date();
      const isRecentPost = (p) => {
        const raw = p.timestamp || p.date;
        if (!raw) return false;
        const d = new Date(raw);
        const t = d.getTime();
        if (isNaN(t)) return false;
        const sameLocalDay = d.toDateString() === now.toDateString();
        const sameUtcDay = d.toISOString().split('T')[0] === now.toISOString().split('T')[0];
        const within24h = (now.getTime() - t) >= 0 && (now.getTime() - t) <= 24 * 3600 * 1000;
        return sameLocalDay || sameUtcDay || within24h;
      };

      const recentPosted = realPosted.filter(isRecentPost);

      lastTodayCounts = {
        ig1: recentPosted.filter(p => p.account === 'ig1').length,
        ig2: recentPosted.filter(p => p.account === 'ig2').length,
        youtube: recentPosted.filter(p => p.account === 'youtube').length
      };

      const totalMb = (totalMediaBytes / (1024 * 1024)).toFixed(1);
      const storagePct = ((totalMediaBytes / (1500 * 1024 * 1024)) * 100).toFixed(1);

      const storageValEl = document.getElementById('storage-stat-val');
      const storageDescEl = document.getElementById('storage-stat-desc');

      updateTopStatCards();
      if (storageValEl) storageValEl.innerHTML = `${totalMb} MB <small class="text-dim-unit">/ 1500 MB</small>`;
      if (storageDescEl) storageDescEl.innerText = `${storagePct}% used • Archive retained for 7 days`;

      // Update Live Cooldown Timers from exact ISO timestamps
      updateCooldownDisplays();

      // Diff data against last sync to prevent unnecessary DOM destruction
      const currentSignature = (
        realPipeline.map(c => `${c.id}:${c.priority}:${c.discarded}:${c.caption}`).join(';') +
        '###' +
        realPosted.map(p => `${p.id}:${p.status}`).join(';')
      );
      const dataChanged = currentSignature !== lastSyncSignature;
      lastSyncSignature = currentSignature;

      // Guard: If preview modal is open, NEVER rebuild DOM underneath the active player!
      if (isPreviewModalActive) {
        pendingRenderAfterModal = true;
      } else if (dataChanged || isManual) {
        calculateDynamicSpacing();
        renderCalendar();
        renderPipelineQueue();
        renderDiscardedQueue();
      }

      lastSyncDate = new Date();
      const timeStr = lastSyncDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

      if (dot) dot.className = 'dot online';
      if (statusText) statusText.innerText = 'Connected';
      const pill = document.getElementById('conn-status-pill');
      if (pill) {
        pill.title = `${auth.repo} (Synced ${timeStr})\nQueue: ${pipelineClips.length} • Posted: ${postedClips.length}\nClick to configure PAT/repo`;
      }
    } catch (err) {
      console.error('GitHub API Sync Error:', err);
      if (dot) dot.className = 'dot danger';
      if (statusText) statusText.innerText = 'Auth Error';
      const pill = document.getElementById('conn-status-pill');
      if (pill) pill.title = `${err.message || 'Check Token'}\nClick to configure PAT/repo`;
      if (isManual) {
        alert(`GitHub Sync Failed: ${err.message || 'Could not connect'}\n\nPlease verify that your token has 'repo' and 'workflow' scopes.`);
      }
    } finally {
      isSyncing = false;
      if (syncIcon) syncIcon.classList.remove('spin-icon');
    }
  }

  function updateTrialDesc() {
    const descEl = document.getElementById('desc-ig1-trial');
    if (descEl) {
      const total = safeInt(settings.ig1Posts, 0);
      const trial = Math.min(total, safeInt(settings.ig1TrialPosts, 0));
      const reg = Math.max(0, total - trial);
      descEl.innerText = total === 0
        ? 'Account paused (0 posts/day)'
        : `${trial} of ${total} posts will test with non-followers (${reg} standard reel${reg === 1 ? '' : 's'})`;
    }
  }

  function updateCooldownDisplays() {
    const now = new Date();

    let lastIg1Ts = null;
    let lastIg2Ts = null;
    let lastYtTs = null;

    postedClips.forEach(p => {
      const rawDate = p.timestamp || p.date;
      if (!rawDate) return;
      const t = new Date(rawDate).getTime();
      if (isNaN(t)) return;

      if (p.account === 'ig1') {
        if (!lastIg1Ts || t > lastIg1Ts) lastIg1Ts = t;
      } else if (p.account === 'ig2') {
        if (!lastIg2Ts || t > lastIg2Ts) lastIg2Ts = t;
      } else if (p.account === 'youtube') {
        if (!lastYtTs || t > lastYtTs) lastYtTs = t;
      }
    });

    // Dynamic Interval Formula: (24h / posts_per_day) - 1.5h buffer
    function getAccountIntervalMinutes(postsPerDay) {
      const n = safeInt(postsPerDay, 0);
      if (n <= 0) return Infinity;
      return Math.max(15, Math.round((24 * 60 / n) - 90));
    }

    const ig1N = safeInt(settings.ig1Posts, 0);
    const ig2N = safeInt(settings.ig2Posts, 0);
    const ytN = safeInt(settings.ytPosts, 0);

    const ig1MinGap = getAccountIntervalMinutes(ig1N);
    const ig2MinGap = getAccountIntervalMinutes(ig2N);
    const ytMinGap = getAccountIntervalMinutes(ytN);

    function computeDesc(lastTs, gapMinutes, prefix = '') {
      if (!lastTs) {
        return { text: prefix ? `${prefix} • Cooldown: Ready` : 'Cooldown: Ready', isReady: true };
      }
      const elapsedMinutes = Math.floor((now.getTime() - lastTs) / (1000 * 60));
      if (elapsedMinutes < 0 || elapsedMinutes >= gapMinutes) {
        const agoStr = elapsedMinutes < 60 ? `${Math.max(0, elapsedMinutes)}m ago` : `${Math.floor(elapsedMinutes / 60)}h ${elapsedMinutes % 60}m ago`;
        return { text: prefix ? `${prefix} • Ready (Last: ${agoStr})` : `Cooldown: Ready (Last: ${agoStr})`, isReady: true };
      }
      const remMinutes = Math.max(1, Math.ceil(gapMinutes - elapsedMinutes));
      const remH = Math.floor(remMinutes / 60);
      const remM = remMinutes % 60;
      const remStr = remH > 0 ? `${remH}h ${remM}m` : `${remM}m`;
      const agoStr = elapsedMinutes < 60 ? `${elapsedMinutes}m ago` : `${Math.floor(elapsedMinutes / 60)}h ${elapsedMinutes % 60}m ago`;
      return { text: `Posted ${agoStr} • Cooldown: ${remStr} remaining`, isReady: false };
    }

    const ig1DescEl = document.getElementById('ig1-stat-desc');
    const ig2DescEl = document.getElementById('ig2-stat-desc');
    const ytDescEl = document.getElementById('yt-stat-desc');

    if (ig1DescEl) {
      if (ig1N <= 0) {
        ig1DescEl.innerText = 'Paused • 0 Posts/day';
        ig1DescEl.classList.remove('highlight');
      } else {
        const trial = safeInt(settings.ig1TrialPosts, 0);
        const prefix = trial > 0 ? 'Trial Eligible' : 'Regular Reels';
        const info = computeDesc(lastIg1Ts, ig1MinGap, prefix);
        ig1DescEl.innerText = info.text;
        if (info.isReady) ig1DescEl.classList.add('highlight');
        else ig1DescEl.classList.remove('highlight');
      }
    }

    if (ig2DescEl) {
      if (ig2N <= 0) {
        ig2DescEl.innerText = 'Paused • 0 Posts/day';
        ig2DescEl.classList.remove('highlight');
      } else {
        const info = computeDesc(lastIg2Ts, ig2MinGap, 'Regular Reels');
        ig2DescEl.innerText = info.text;
        if (info.isReady) ig2DescEl.classList.add('highlight');
        else ig2DescEl.classList.remove('highlight');
      }
    }

    if (ytDescEl) {
      if (ytN <= 0) {
        ytDescEl.innerText = 'Paused • 0 Shorts/day';
        ytDescEl.classList.remove('highlight');
      } else {
        const info = computeDesc(lastYtTs, ytMinGap, 'YouTube Shorts');
        ytDescEl.innerText = info.text;
        if (info.isReady) ytDescEl.classList.add('highlight');
        else ytDescEl.classList.remove('highlight');
      }
    }
  }

  function renderCategoryChips() {
    const prioWrap = document.getElementById('prio-cat-chips');
    const deprioWrap = document.getElementById('deprio-cat-chips');

    if (prioWrap) {
      const list = settings.prioritizedCategories || [];
      if (list.length === 0) {
        prioWrap.innerHTML = '<span style="font-size:11px;color:var(--text-dim);font-style:italic;">No prioritized categories configured.</span>';
      } else {
        prioWrap.innerHTML = '';
        list.forEach(cat => {
          const chip = document.createElement('span');
          chip.className = 'cat-chip chip-prio';
          chip.innerHTML = `<span>${cat}</span><button type="button" class="cat-chip-remove" title="Remove">&times;</button>`;
          chip.querySelector('.cat-chip-remove').onclick = () => {
            settings.prioritizedCategories = settings.prioritizedCategories.filter(c => c !== cat);
            safeSetStorage(STORAGE_KEY_SETTINGS, settings);
            renderCategoryChips();
            calculateDynamicSpacing();
            renderPipelineQueue();
            renderCalendar();
          };
          prioWrap.appendChild(chip);
        });
      }
    }

    if (deprioWrap) {
      const list = settings.deprioritizedCategories || [];
      if (list.length === 0) {
        deprioWrap.innerHTML = '<span style="font-size:11px;color:var(--text-dim);font-style:italic;">No deprioritized categories configured.</span>';
      } else {
        deprioWrap.innerHTML = '';
        list.forEach(cat => {
          const chip = document.createElement('span');
          chip.className = 'cat-chip chip-deprio';
          chip.innerHTML = `<span>${cat}</span><button type="button" class="cat-chip-remove" title="Remove">&times;</button>`;
          chip.querySelector('.cat-chip-remove').onclick = () => {
            settings.deprioritizedCategories = settings.deprioritizedCategories.filter(c => c !== cat);
            safeSetStorage(STORAGE_KEY_SETTINGS, settings);
            renderCategoryChips();
            calculateDynamicSpacing();
            renderPipelineQueue();
            renderCalendar();
          };
          deprioWrap.appendChild(chip);
        });
      }
    }
  }

  function syncSettingsControlsToUI() {
    const setSliderVal = (sId, vId, val, suffix = '', showPaused = false) => {
      const s = document.getElementById(sId);
      const v = document.getElementById(vId);
      if (s) s.value = val;
      if (v) {
        v.innerText = showPaused ? formatSliderVal(val) : `${val}${suffix}`;
        if (showPaused) v.classList.toggle('val-paused', safeInt(val, 0) === 0);
      }
    };

    setSliderVal('slider-ig1', 'val-ig1', settings.ig1Posts, '', true);
    const s1Trial = document.getElementById('slider-ig1-trial');
    if (s1Trial) s1Trial.max = settings.ig1Posts;
    setSliderVal('slider-ig1-trial', 'val-ig1-trial', settings.ig1TrialPosts, '', false);
    setSliderVal('slider-ig2', 'val-ig2', settings.ig2Posts, '', true);
    setSliderVal('slider-yt', 'val-yt', settings.ytPosts, '', true);
    setSliderVal('slider-stream-yield', 'val-stream-yield', settings.streamYield, '', false);
    setSliderVal('slider-clip-spacing', 'val-clip-spacing', settings.clipSpacing, 's', false);

    const nsfwToggle = document.getElementById('toggle-nsfw-censor');
    if (nsfwToggle) nsfwToggle.checked = Boolean(settings.autoCensorNsfw);
    const censorSel = document.getElementById('select-censor-mode');
    if (censorSel) censorSel.value = settings.censorMode || 'blur';

    updateTrialDesc();
    renderCategoryChips();
  }

  function applyRemoteConfig(cfg) {
    if (activeTab === 'settings' || isSettingsDirty || document.querySelector('#view-settings.active') || document.activeElement?.closest('#view-settings')) {
      // Do not overwrite user controls while user is actively editing or reviewing settings
      return;
    }
    const sched = cfg.publishing_schedule || {};
    const igAccounts = sched.instagram_accounts || [];

    const ig1 = igAccounts.find(a => a.slot === 1);
    if (ig1) {
      const reg = safeInt(ig1.regular_per_day, 0);
      const trial = safeInt(ig1.trial_per_day, 0);
      settings.ig1Posts = ig1.enabled === false ? 0 : (reg + trial);
      settings.ig1TrialPosts = ig1.enabled === false ? 0 : Math.min(settings.ig1Posts, trial);
    }

    const ig2 = igAccounts.find(a => a.slot === 2);
    if (ig2) {
      settings.ig2Posts = ig2.enabled === false ? 0 : safeInt(ig2.regular_per_day, 0);
    }

    const yt = sched.youtube || {};
    if (yt) {
      settings.ytPosts = yt.enabled === false ? 0 : safeInt(yt.shorts_per_day, 3);
    }

    if (sched.priority_rules) {
      if (Array.isArray(sched.priority_rules.prioritized_categories)) {
        settings.prioritizedCategories = [...sched.priority_rules.prioritized_categories];
      }
      if (Array.isArray(sched.priority_rules.deprioritized_categories)) {
        settings.deprioritizedCategories = [...sched.priority_rules.deprioritized_categories];
      }
    }

    const tc = cfg.twitch_clipper || {};
    if (typeof tc.max_clips_per_vod !== 'undefined') {
      settings.streamYield = safeInt(tc.max_clips_per_vod, 10);
    }
    if (typeof tc.min_clip_spacing_sec !== 'undefined') {
      settings.clipSpacing = safeInt(tc.min_clip_spacing_sec, 300);
    }

    const safety = cfg.content_safety || {};
    if (typeof safety.auto_censor_nsfw === 'boolean') {
      settings.autoCensorNsfw = safety.auto_censor_nsfw;
    }
    if (safety.censor_mode) {
      settings.censorMode = safety.censor_mode;
    }

    const expiry = sched.token_expiry_date || (ig1 && ig1.token_expiry_date) || (ig2 && ig2.token_expiry_date) || '2027-01-17';
    settings.tokenExpiryDate = expiry;

    safeSetStorage(STORAGE_KEY_SETTINGS, settings);
    syncSettingsControlsToUI();
    renderTokenExpiryAlerts();
    calculateDynamicSpacing();
  }

  function loadDemoData() {
    pipelineClips = [...DEMO_PIPELINE];
    postedClips = [...DEMO_POSTED];
    pipelineClips.forEach(c => applyOverridesToClip(c));
    pipelineClips = pipelineClips.filter(c => !c._deleted);
    calculateDynamicSpacing();
    renderCalendar();
    renderPipelineQueue();
    renderDiscardedQueue();
  }

  // --- Initializer & Event Binding ---
  function initUI() {
    // 1. Navigation Tabs
    document.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.main-view').forEach(v => {
          v.classList.remove('active');
          v.style.display = 'none';
        });

        btn.classList.add('active');
        activeTab = btn.dataset.tab;
        const targetView = document.getElementById(`view-${activeTab}`);
        if (targetView) {
          targetView.classList.add('active');
          targetView.style.display = 'block';
        }

        if (activeTab === 'calendar') renderCalendar();
        if (activeTab === 'pipeline') renderPipelineQueue();
        if (activeTab === 'discarded') renderDiscardedQueue();
      });
    });

    // 2. Calendar View Switchers
    document.querySelectorAll('.view-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.view-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        activeCalView = btn.dataset.calView;
        renderCalendar();
      });
    });

    // 3. Calendar Date Navigation
    const calPrev = document.getElementById('cal-prev');
    const calNext = document.getElementById('cal-next');
    const calToday = document.getElementById('cal-today');

    if (calPrev) {
      calPrev.addEventListener('click', () => {
        if (activeCalView === 'week') currentDate.setDate(currentDate.getDate() - 7);
        else if (activeCalView === 'day') currentDate.setDate(currentDate.getDate() - 1);
        else if (activeCalView === 'month') {
          currentDate.setDate(1);
          currentDate.setMonth(currentDate.getMonth() - 1);
        }
        renderCalendar();
      });
    }

    if (calNext) {
      calNext.addEventListener('click', () => {
        if (activeCalView === 'week') currentDate.setDate(currentDate.getDate() + 7);
        else if (activeCalView === 'day') currentDate.setDate(currentDate.getDate() + 1);
        else if (activeCalView === 'month') {
          currentDate.setDate(1);
          currentDate.setMonth(currentDate.getMonth() + 1);
        }
        renderCalendar();
      });
    }

    if (calToday) {
      calToday.addEventListener('click', () => {
        currentDate = new Date();
        renderCalendar();
      });
    }

    // 4. Filter Pills
    document.querySelectorAll('.filter-pills .pill').forEach(pill => {
      pill.addEventListener('click', () => {
        document.querySelectorAll('.filter-pills .pill').forEach(p => p.classList.remove('active'));
        pill.classList.add('active');
        activeFilter = pill.dataset.filter;
        renderCalendar();
      });
    });

    // 5. Setup & Auth Modal Trigger Bindings
    const btnOpenSetup = document.getElementById('btn-open-setup');
    if (btnOpenSetup) {
      btnOpenSetup.onclick = (e) => {
        e.preventDefault();
        window.openSetupModal();
      };
    }

    const connStatusPill = document.getElementById('conn-status-pill');
    if (connStatusPill) {
      connStatusPill.onclick = () => window.openSetupModal();
    }

    const btnCloseSetup = document.getElementById('btn-close-setup');
    if (btnCloseSetup) {
      btnCloseSetup.onclick = () => window.closeSetupModal();
    }

    const modalSetup = document.getElementById('modal-setup');
    if (modalSetup) {
      modalSetup.onclick = (e) => {
        if (e.target === modalSetup) window.closeSetupModal();
      };
    }

    const btnSavePat = document.getElementById('btn-save-pat');
    if (btnSavePat) {
      btnSavePat.addEventListener('click', () => {
        const pat = (document.getElementById('setup-pat')?.value || '').trim();
        const repo = (document.getElementById('setup-repo')?.value || '').trim();
        const branch = (document.getElementById('setup-branch')?.value || 'master').trim();
        const contentBranch = (document.getElementById('setup-content-branch')?.value || 'content').trim();

        if (!pat) {
          alert('Please enter a GitHub Personal Access Token or choose Explore with Demo Data.');
          return;
        }

        auth = { pat, repo, branch, contentBranch, isDemo: false };
        safeSetStorage(STORAGE_KEY_AUTH, auth);
        window.closeSetupModal();
        syncWithGitHub();
      });
    }

    const btnUseDemo = document.getElementById('btn-use-demo');
    if (btnUseDemo) {
      btnUseDemo.addEventListener('click', () => {
        auth.isDemo = true;
        auth.pat = '';
        safeSetStorage(STORAGE_KEY_AUTH, auth);
        window.closeSetupModal();
        loadDemoData();
      });
    }

    // 6. Preview Modal Backdrop & Escape Key Handlers
    const modalPreview = document.getElementById('modal-preview');
    if (modalPreview) {
      modalPreview.onclick = (e) => {
        if (e.target === modalPreview) window.closePreviewModal();
      };
    }

    const btnClosePreview = document.getElementById('btn-close-preview');
    if (btnClosePreview) {
      btnClosePreview.onclick = () => window.closePreviewModal();
    }

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        window.closeSetupModal();
        window.closePreviewModal();
      }
    });

    const btnSaveCaption = document.getElementById('btn-save-caption');
    if (btnSaveCaption) {
      btnSaveCaption.addEventListener('click', () => {
        if (selectedClip) {
          setClipPriority(selectedClip, selectedClip.priority, true);
          window.closePreviewModal();
        }
      });
    }

    const btnDiscardClip = document.getElementById('btn-discard-clip');
    if (btnDiscardClip) {
      btnDiscardClip.addEventListener('click', () => {
        if (selectedClip) discardClip(selectedClip, true);
      });
    }

    const btnPurgeExpired = document.getElementById('btn-purge-expired-discarded');
    if (btnPurgeExpired) {
      btnPurgeExpired.addEventListener('click', () => {
        purgeExpiredDiscarded();
      });
    }

    // Preview Modal 5-Tier Priority Buttons (1 to 5)
    document.querySelectorAll('#preview-priority-controls .prio-select-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        if (selectedClip) {
          setClipPriority(selectedClip, btn.dataset.setPriority, true);
        }
      });
    });

    // Pipeline Priority Filter Bar (All, 5, 4, 3, 2, 1)
    document.querySelectorAll('#pipeline-priority-filters .pill').forEach(pill => {
      pill.addEventListener('click', () => {
        document.querySelectorAll('#pipeline-priority-filters .pill').forEach(p => p.classList.remove('active'));
        pill.classList.add('active');
        activePrioFilter = pill.dataset.prioFilter || 'all';
        renderPipelineQueue();
      });
    });

    // Start Real-Time Current Time Indicator Loop
    setInterval(updateCurrentTimeIndicator, 30000);

    // 7. Settings Sliders (Zero-safe: supports 0..8 cleanly)
    const bindSlider = (id, valId, key, suffix = '', showPaused = false) => {
      const el = document.getElementById(id);
      const valEl = document.getElementById(valId);
      if (!el || !valEl) return;

      const curVal = safeInt(settings[key], 0);
      el.value = curVal;
      valEl.innerText = showPaused ? formatSliderVal(curVal) : `${curVal}${suffix}`;
      if (showPaused) valEl.classList.toggle('val-paused', curVal === 0);

      el.addEventListener('input', () => {
        isSettingsDirty = true;
        const v = safeInt(el.value, 0);
        valEl.innerText = showPaused ? formatSliderVal(v) : `${v}${suffix}`;
        if (showPaused) valEl.classList.toggle('val-paused', v === 0);
        settings[key] = v;
        safeSetStorage(STORAGE_KEY_SETTINGS, settings);
        calculateDynamicSpacing();
        renderCalendar();
        renderPipelineQueue();
      });
    };

    // Specialized Slider for Instagram 1 and Dynamic Trial Allocation
    const sliderIg1 = document.getElementById('slider-ig1');
    const valIg1 = document.getElementById('val-ig1');
    const sliderIg1Trial = document.getElementById('slider-ig1-trial');
    const valIg1Trial = document.getElementById('val-ig1-trial');

    if (sliderIg1) {
      const initIg1 = safeInt(settings.ig1Posts, 0);
      sliderIg1.value = initIg1;
      if (valIg1) {
        valIg1.innerText = formatSliderVal(initIg1);
        valIg1.classList.toggle('val-paused', initIg1 === 0);
      }

      sliderIg1.addEventListener('input', () => {
        isSettingsDirty = true;
        const total = safeInt(sliderIg1.value, 0);
        if (valIg1) {
          valIg1.innerText = formatSliderVal(total);
          valIg1.classList.toggle('val-paused', total === 0);
        }
        settings.ig1Posts = total;

        // Dynamically clamp Trial Reels Share between 0 and total posts
        if (sliderIg1Trial) {
          sliderIg1Trial.max = total;
          if (settings.ig1TrialPosts > total) {
            settings.ig1TrialPosts = total;
            sliderIg1Trial.value = total;
            if (valIg1Trial) valIg1Trial.innerText = total;
          }
        }
        updateTrialDesc();
        safeSetStorage(STORAGE_KEY_SETTINGS, settings);
        calculateDynamicSpacing();
        renderCalendar();
        renderPipelineQueue();
      });
    }

    if (sliderIg1Trial) {
      const initIg1 = safeInt(settings.ig1Posts, 0);
      const initTrial = Math.min(initIg1, safeInt(settings.ig1TrialPosts, 0));
      sliderIg1Trial.max = initIg1;
      sliderIg1Trial.value = initTrial;
      if (valIg1Trial) valIg1Trial.innerText = initTrial;
      updateTrialDesc();

      sliderIg1Trial.addEventListener('input', () => {
        isSettingsDirty = true;
        const trial = safeInt(sliderIg1Trial.value, 0);
        if (valIg1Trial) valIg1Trial.innerText = trial;
        settings.ig1TrialPosts = trial;
        updateTrialDesc();
        safeSetStorage(STORAGE_KEY_SETTINGS, settings);
        calculateDynamicSpacing();
        renderCalendar();
        renderPipelineQueue();
      });
    }

    bindSlider('slider-ig2', 'val-ig2', 'ig2Posts', '', true);
    bindSlider('slider-yt', 'val-yt', 'ytPosts', '', true);
    bindSlider('slider-stream-yield', 'val-stream-yield', 'streamYield');
    bindSlider('slider-clip-spacing', 'val-clip-spacing', 'clipSpacing', 's');

    // Stepper Buttons (- / +) for Daily Post Counts (0..5)
    document.querySelectorAll('.btn-stepper').forEach(btn => {
      btn.addEventListener('click', () => {
        isSettingsDirty = true;
        const targetId = btn.dataset.stepTarget;
        const delta = safeInt(btn.dataset.step, 0);
        const slider = document.getElementById(targetId);
        if (!slider) return;
        const min = safeInt(slider.min, 0);
        const max = safeInt(slider.max, 5);
        const nextVal = Math.max(min, Math.min(max, safeInt(slider.value, 0) + delta));
        slider.value = nextVal;
        slider.dispatchEvent(new Event('input', { bubbles: true }));
      });
    });

    // Category / Game Priority Tag Managers
    function addPriorityCategory(targetListKey, rawText) {
      const items = String(rawText || '').split(',').map(s => s.trim()).filter(Boolean);
      if (items.length === 0) return;
      if (!Array.isArray(settings[targetListKey])) settings[targetListKey] = [];
      const otherKey = targetListKey === 'prioritizedCategories' ? 'deprioritizedCategories' : 'prioritizedCategories';
      if (!Array.isArray(settings[otherKey])) settings[otherKey] = [];

      items.forEach(item => {
        const lower = item.toLowerCase();
        // Remove from opposite list if present so rules never conflict
        settings[otherKey] = settings[otherKey].filter(x => x.toLowerCase() !== lower);
        if (!settings[targetListKey].some(x => x.toLowerCase() === lower)) {
          settings[targetListKey].push(item);
        }
      });
      safeSetStorage(STORAGE_KEY_SETTINGS, settings);
      renderCategoryChips();
      calculateDynamicSpacing();
      renderPipelineQueue();
      renderCalendar();
    }

    const inputPrioCat = document.getElementById('input-prio-cat');
    const btnAddPrioCat = document.getElementById('btn-add-prio-cat');
    if (btnAddPrioCat && inputPrioCat) {
      btnAddPrioCat.addEventListener('click', () => {
        addPriorityCategory('prioritizedCategories', inputPrioCat.value);
        inputPrioCat.value = '';
      });
      inputPrioCat.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          addPriorityCategory('prioritizedCategories', inputPrioCat.value);
          inputPrioCat.value = '';
        }
      });
    }

    const inputDeprioCat = document.getElementById('input-deprio-cat');
    const btnAddDeprioCat = document.getElementById('btn-add-deprio-cat');
    if (btnAddDeprioCat && inputDeprioCat) {
      btnAddDeprioCat.addEventListener('click', () => {
        addPriorityCategory('deprioritizedCategories', inputDeprioCat.value);
        inputDeprioCat.value = '';
      });
      inputDeprioCat.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          addPriorityCategory('deprioritizedCategories', inputDeprioCat.value);
          inputDeprioCat.value = '';
        }
      });
    }

    document.querySelectorAll('.preset-chip').forEach(chip => {
      chip.addEventListener('click', () => {
        const target = chip.dataset.presetTarget === 'deprioritized' ? 'deprioritizedCategories' : 'prioritizedCategories';
        addPriorityCategory(target, chip.dataset.presetVal);
      });
    });

    // Content Safety / NSFW Censor Controls
    const nsfwToggle = document.getElementById('toggle-nsfw-censor');
    if (nsfwToggle) {
      nsfwToggle.checked = Boolean(settings.autoCensorNsfw);
      nsfwToggle.addEventListener('change', () => {
        settings.autoCensorNsfw = nsfwToggle.checked;
        safeSetStorage(STORAGE_KEY_SETTINGS, settings);
      });
    }
    const censorSel = document.getElementById('select-censor-mode');
    if (censorSel) {
      censorSel.value = settings.censorMode || 'blur';
      censorSel.addEventListener('change', () => {
        settings.censorMode = censorSel.value;
        safeSetStorage(STORAGE_KEY_SETTINGS, settings);
      });
    }

    renderCategoryChips();

    // 8. Hype Mode Toggle
    const hypeToggle = document.getElementById('toggle-hype');
    if (hypeToggle) {
      hypeToggle.addEventListener('change', () => {
        settings.hypeMode = hypeToggle.checked;
        if (settings.hypeMode) {
          settings.ytPosts = Math.max(4, settings.ytPosts);
          if (settings.ig1Posts > 0) settings.ig1Posts = 4;
          if (settings.ig2Posts > 0) settings.ig2Posts = 4;
        } else {
          if (settings.ytPosts > 3) settings.ytPosts = 3;
          if (settings.ig1Posts > 3) settings.ig1Posts = 3;
          if (settings.ig2Posts > 3) settings.ig2Posts = 3;
        }
        syncSettingsControlsToUI();
        safeSetStorage(STORAGE_KEY_SETTINGS, settings);
        calculateDynamicSpacing();
        renderCalendar();
      });
    }

    // 9. Save Settings Button (Writes ALL daily counts including 0, priority rules, & NSFW shield to GitHub config.json)
    const btnSaveSettings = document.getElementById('btn-save-settings');
    if (btnSaveSettings) {
      btnSaveSettings.addEventListener('click', async () => {
        safeSetStorage(STORAGE_KEY_SETTINGS, settings);

        if (auth.pat && !auth.isDemo) {
          try {
            btnSaveSettings.disabled = true;
            btnSaveSettings.innerText = 'Saving to GitHub...';
            const headers = {
              'Authorization': `token ${auth.pat.trim()}`,
              'Accept': 'application/vnd.github.v3+json',
              'Content-Type': 'application/json'
            };
            const noCacheHeaders = {
              ...headers,
              'Cache-Control': 'no-cache, no-store, must-revalidate',
              'Pragma': 'no-cache'
            };
            const pBranch = auth.branch || 'master';

            // 1. Get current config.json with cache-busting to get true latest sha and structure
            const curRes = await fetch(`https://api.github.com/repos/${auth.repo}/contents/config.json?ref=${pBranch}&_t=${Date.now()}`, {
              headers: noCacheHeaders
            });
            if (!curRes.ok) {
              const errJson = await curRes.json().catch(() => ({}));
              throw new Error(errJson.message || `Could not read config.json (HTTP ${curRes.status})`);
            }
            const curData = await curRes.json();
            const curStr = decodeURIComponent(escape(atob(curData.content)));
            const cfg = JSON.parse(curStr);

            const applyFormToConfig = (targetCfg) => {
              if (!targetCfg.publishing_schedule) targetCfg.publishing_schedule = {};
              if (!targetCfg.publishing_schedule.youtube) targetCfg.publishing_schedule.youtube = {};
              const ytN = Math.max(0, safeInt(settings.ytPosts, 0));
              targetCfg.publishing_schedule.youtube.enabled = ytN > 0;
              targetCfg.publishing_schedule.youtube.shorts_per_day = ytN;
              targetCfg.publishing_schedule.youtube.hard_daily_ceiling = ytN;

              if (Array.isArray(targetCfg.publishing_schedule.instagram_accounts)) {
                const ig1N = Math.max(0, safeInt(settings.ig1Posts, 0));
                const ig1Trial = Math.min(ig1N, Math.max(0, safeInt(settings.ig1TrialPosts, 0)));
                const acc1 = targetCfg.publishing_schedule.instagram_accounts.find(a => a.slot === 1);
                if (acc1) {
                  acc1.enabled = ig1N > 0;
                  acc1.trial_per_day = ig1Trial;
                  acc1.regular_per_day = Math.max(0, ig1N - ig1Trial);
                  acc1.hard_daily_ceiling = ig1N;
                  if (ig1N > 0) delete acc1.disabled_reason;
                }

                const ig2N = Math.max(0, safeInt(settings.ig2Posts, 0));
                const acc2 = targetCfg.publishing_schedule.instagram_accounts.find(a => a.slot === 2);
                if (acc2) {
                  acc2.enabled = ig2N > 0;
                  acc2.regular_per_day = ig2N;
                  acc2.trial_per_day = 0;
                  acc2.hard_daily_ceiling = ig2N;
                  if (ig2N > 0) delete acc2.disabled_reason;
                }
              }

              targetCfg.publishing_schedule.token_expiry_date = settings.tokenExpiryDate || '2027-01-17';
              if (Array.isArray(targetCfg.publishing_schedule.instagram_accounts)) {
                targetCfg.publishing_schedule.instagram_accounts.forEach(a => {
                  a.token_expiry_date = settings.tokenExpiryDate || '2027-01-17';
                });
              }

              targetCfg.publishing_schedule.priority_rules = {
                prioritized_categories: [...(settings.prioritizedCategories || [])],
                deprioritized_categories: [...(settings.deprioritizedCategories || [])]
              };

              if (!targetCfg.twitch_clipper) targetCfg.twitch_clipper = {};
              targetCfg.twitch_clipper.max_clips_per_vod = safeInt(settings.streamYield, 10);
              targetCfg.twitch_clipper.min_clip_spacing_sec = safeInt(settings.clipSpacing, 300);

              targetCfg.content_safety = {
                ...(targetCfg.content_safety || {}),
                auto_censor_nsfw: Boolean(settings.autoCensorNsfw),
                censor_mode: settings.censorMode || 'blur',
                max_nsfw_ratio_before_reject: (targetCfg.content_safety && targetCfg.content_safety.max_nsfw_ratio_before_reject) || 0.65
              };
            };

            applyFormToConfig(cfg);
            const ytN = Math.max(0, safeInt(settings.ytPosts, 0));
            const updatedJsonStr = JSON.stringify(cfg, null, 2);
            const b64 = btoa(unescape(encodeURIComponent(updatedJsonStr)));

            // Commit updated config.json to GitHub
            let putRes = await fetch(`https://api.github.com/repos/${auth.repo}/contents/config.json`, {
              method: 'PUT',
              headers,
              body: JSON.stringify({
                message: `chore(config): update daily limits (YT=${ytN}, IG1=${settings.ig1Posts}, IG2=${settings.ig2Posts}) & priority rules via dashboard`,
                content: b64,
                sha: curData.sha,
                branch: pBranch
              })
            });

            // If 409 conflict or 422 SHA mismatch occurs, fetch fresh sha directly and retry once
            if (putRes.status === 409 || putRes.status === 422) {
              const freshRes = await fetch(`https://api.github.com/repos/${auth.repo}/contents/config.json?ref=${pBranch}&_t=${Date.now()}`, {
                headers: noCacheHeaders
              });
              if (freshRes.ok) {
                const freshData = await freshRes.json();
                const freshStr = decodeURIComponent(escape(atob(freshData.content)));
                const freshCfg = JSON.parse(freshStr);
                applyFormToConfig(freshCfg);
                const freshJsonStr = JSON.stringify(freshCfg, null, 2);
                const freshB64 = btoa(unescape(encodeURIComponent(freshJsonStr)));

                putRes = await fetch(`https://api.github.com/repos/${auth.repo}/contents/config.json`, {
                  method: 'PUT',
                  headers,
                  body: JSON.stringify({
                    message: `chore(config): update daily limits (YT=${ytN}, IG1=${settings.ig1Posts}, IG2=${settings.ig2Posts}) & priority rules via dashboard`,
                    content: freshB64,
                    sha: freshData.sha,
                    branch: pBranch
                  })
                });
              }
            }

            if (putRes.ok) {
              isSettingsDirty = false;
              calculateDynamicSpacing();
              renderCalendar();
              renderPipelineQueue();
              alert(`Settings saved to GitHub (${pBranch}/config.json)!\n\n• YouTube Shorts: ${ytN}/day\n• IG @solvikz: ${settings.ig1Posts}/day\n• IG @loopablez: ${settings.ig2Posts}/day\n• Prioritized Categories: ${(settings.prioritizedCategories || []).join(', ') || 'None'}\n• Deprioritized Categories: ${(settings.deprioritizedCategories || []).join(', ') || 'None'}`);
            } else {
              const errJson = await putRes.json().catch(() => ({}));
              throw new Error(errJson.message || `GitHub commit failed (HTTP ${putRes.status})`);
            }
          } catch (e) {
            console.error('Failed to commit config to GitHub:', e);
            alert(`Failed to save to GitHub: ${e.message}\n\nSettings were saved locally in browser, but NOT committed to GitHub. Check your PAT permissions (needs 'repo' write scope).`);
          } finally {
            btnSaveSettings.disabled = false;
            btnSaveSettings.innerHTML = '<svg class="icon" viewBox="0 0 24 24"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg> Save Settings to Repository';
          }
        } else {
          calculateDynamicSpacing();
          renderCalendar();
          renderPipelineQueue();
          alert('Demo Mode: Settings saved locally in browser. Connect a GitHub PAT in Setup to commit changes to config.json.');
        }
      });
    }

    // 10. Diagnostics and Action Triggers
    const btnSync = document.getElementById('btn-sync');
    if (btnSync) btnSync.addEventListener('click', () => syncWithGitHub(true));

    // Generic helper to dispatch GitHub Actions workflows via GitHub API
    async function triggerGitHubWorkflow(workflowFile, inputs = {}) {
      if (!auth.pat || auth.isDemo) {
        alert('GitHub Personal Access Token required.\n\nPlease open Setup and enter a PAT with "repo" and "workflow" scopes.');
        return false;
      }
      const repo = auth.repo || 'Deeptanil/HyperClip-AI';
      const branch = auth.branch || 'master';
      const headers = {
        'Authorization': `token ${auth.pat.trim()}`,
        'Accept': 'application/vnd.github.v3+json',
        'Content-Type': 'application/json'
      };
      const res = await fetch(`https://api.github.com/repos/${repo}/actions/workflows/${workflowFile}/dispatches`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          ref: branch,
          inputs: inputs
        })
      });
      if (res.status === 204 || res.ok) {
        return true;
      }
      const err = await res.json().catch(() => ({}));
      throw new Error(err.message || `HTTP ${res.status}`);
    }

    const btnRunAction = document.getElementById('btn-run-action');
    if (btnRunAction) {
      btnRunAction.addEventListener('click', async () => {
        const origHtml = btnRunAction.innerHTML;
        btnRunAction.disabled = true;
        btnRunAction.innerHTML = `<span>Starting...</span>`;
        try {
          await triggerGitHubWorkflow('twitch_clipper.yml', { force: 'false' });
          btnRunAction.innerHTML = `<span>Dispatched!</span>`;
          alert('Successfully triggered Auto-Posting & Clipping cycle on GitHub Actions!\n\nThe runner is starting now. Click Sync in 1-2 minutes to see results.');
          setTimeout(() => syncWithGitHub(), 15000);
        } catch (err) {
          console.error('Failed to trigger workflow:', err);
          alert(`Failed to trigger GitHub Actions workflow: ${err.message}\n\nPlease verify that your PAT in Setup has the "workflow" scope enabled.`);
        } finally {
          setTimeout(() => {
            btnRunAction.disabled = false;
            btnRunAction.innerHTML = origHtml;
          }, 3000);
        }
      });
    }

    const btnHarvestFresh = document.getElementById('btn-harvest-fresh');
    if (btnHarvestFresh) {
      btnHarvestFresh.addEventListener('click', async () => {
        const origHtml = btnHarvestFresh.innerHTML;
        btnHarvestFresh.disabled = true;
        btnHarvestFresh.innerHTML = `<span>Scanning...</span>`;
        try {
          await triggerGitHubWorkflow('twitch_clipper.yml', { harvest_only: 'true' });
          btnHarvestFresh.innerHTML = `<span>Started!</span>`;
          alert('Successfully dispatched Live Stream Scanner on GitHub Actions!\n\nIt is harvesting live Twitch clips and staging them into the pipeline.');
          setTimeout(() => syncWithGitHub(), 30000);
        } catch (err) {
          console.error('Failed to dispatch stream scanner:', err);
          alert(`Failed to trigger stream scanner: ${err.message}\n\nPlease verify that your PAT in Setup has the "workflow" scope enabled.`);
        } finally {
          setTimeout(() => {
            btnHarvestFresh.disabled = false;
            btnHarvestFresh.innerHTML = origHtml;
          }, 3000);
        }
      });
    }

    const btnTestDiag = document.getElementById('btn-test-diag');
    if (btnTestDiag) {
      btnTestDiag.addEventListener('click', async () => {
        const origHtml = btnTestDiag.innerHTML;
        btnTestDiag.disabled = true;
        btnTestDiag.innerHTML = `<span>Testing...</span>`;
        try {
          if (!auth.pat || auth.isDemo) {
            alert('Demo Mode: Enter your GitHub PAT in Setup to test live credentials.');
            return;
          }
          const headers = {
            'Authorization': `token ${auth.pat.trim()}`,
            'Accept': 'application/vnd.github.v3+json'
          };
          const repoRes = await fetch(`https://api.github.com/repos/${auth.repo}`, { headers });
          if (!repoRes.ok) throw new Error(`GitHub token error: ${repoRes.statusText}`);
          const repoData = await repoRes.json();
          alert(`GitHub Connected Successfully!\n\nRepository: ${repoData.full_name}\nDefault Branch: ${repoData.default_branch}\nPermissions: Push=${repoData.permissions?.push || false}, Admin=${repoData.permissions?.admin || false}\n\nAccounts @solvikz, @loopablez, and YouTube credentials are stored securely in GitHub Repository Secrets.`);
        } catch (err) {
          alert(`Credential Diagnostic Failed: ${err.message}`);
        } finally {
          btnTestDiag.disabled = false;
          btnTestDiag.innerHTML = origHtml;
        }
      });
    }

    // 11. Meta Token Expiration Save & Monitoring
    const btnSaveTokenExpiry = document.getElementById('btn-save-token-expiry');
    const inputTokenExpiry = document.getElementById('input-token-expiry');
    if (btnSaveTokenExpiry && inputTokenExpiry) {
      btnSaveTokenExpiry.addEventListener('click', async () => {
        const val = inputTokenExpiry.value;
        if (!val) {
          alert('Please select a valid expiration date.');
          return;
        }
        settings.tokenExpiryDate = val;
        safeSetStorage(STORAGE_KEY_SETTINGS, settings);
        renderTokenExpiryAlerts();

        if (auth.pat && !auth.isDemo) {
          try {
            btnSaveTokenExpiry.disabled = true;
            btnSaveTokenExpiry.innerText = 'Saving...';
            const pBranch = auth.branch || 'master';
            const headers = {
              'Authorization': `token ${auth.pat.trim()}`,
              'Accept': 'application/vnd.github.v3+json',
              'Content-Type': 'application/json'
            };
            const noCacheHeaders = {
              ...headers,
              'Cache-Control': 'no-cache, no-store, must-revalidate',
              'Pragma': 'no-cache'
            };
            let curRes = await fetch(`https://api.github.com/repos/${auth.repo}/contents/config.json?ref=${pBranch}&_t=${Date.now()}`, {
              headers: noCacheHeaders
            });
            if (curRes.ok) {
              let curData = await curRes.json();
              let curStr = decodeURIComponent(escape(atob(curData.content)));
              let cfg = JSON.parse(curStr);
              if (!cfg.publishing_schedule) cfg.publishing_schedule = {};
              cfg.publishing_schedule.token_expiry_date = val;
              if (Array.isArray(cfg.publishing_schedule.instagram_accounts)) {
                cfg.publishing_schedule.instagram_accounts.forEach(a => {
                  a.token_expiry_date = val;
                });
              }
              let b64 = btoa(unescape(encodeURIComponent(JSON.stringify(cfg, null, 2))));
              let putRes = await fetch(`https://api.github.com/repos/${auth.repo}/contents/config.json`, {
                method: 'PUT',
                headers,
                body: JSON.stringify({
                  message: `chore(config): update Meta token expiration date to ${val}`,
                  content: b64,
                  sha: curData.sha,
                  branch: pBranch
                })
              });
              if (putRes.status === 409 || putRes.status === 422) {
                const freshRes = await fetch(`https://api.github.com/repos/${auth.repo}/contents/config.json?ref=${pBranch}&_t=${Date.now()}`, {
                  headers: noCacheHeaders
                });
                if (freshRes.ok) {
                  curData = await freshRes.json();
                  curStr = decodeURIComponent(escape(atob(curData.content)));
                  cfg = JSON.parse(curStr);
                  if (!cfg.publishing_schedule) cfg.publishing_schedule = {};
                  cfg.publishing_schedule.token_expiry_date = val;
                  if (Array.isArray(cfg.publishing_schedule.instagram_accounts)) {
                    cfg.publishing_schedule.instagram_accounts.forEach(a => {
                      a.token_expiry_date = val;
                    });
                  }
                  b64 = btoa(unescape(encodeURIComponent(JSON.stringify(cfg, null, 2))));
                  putRes = await fetch(`https://api.github.com/repos/${auth.repo}/contents/config.json`, {
                    method: 'PUT',
                    headers,
                    body: JSON.stringify({
                      message: `chore(config): update Meta token expiration date to ${val}`,
                      content: b64,
                      sha: curData.sha,
                      branch: pBranch
                    })
                  });
                }
              }
              if (putRes.ok) {
                alert(`Token expiration date (${val}) committed to config.json!`);
              }
            }
          } catch (e) {
            console.error('Failed to commit token expiry to GitHub:', e);
            alert(`Token date saved in browser: ${val}`);
          } finally {
            btnSaveTokenExpiry.disabled = false;
            btnSaveTokenExpiry.innerText = 'Save Expiry Date';
          }
        } else {
          alert(`Token expiration date saved: ${val}\n(Saved locally; connect GitHub PAT in Setup to commit to config.json)`);
        }
      });
    }

    renderTokenExpiryAlerts();
  }

  // --- Initial Startup Execution (Race-Condition Free) ---
  function startApp() {
    initUI();
    if (!auth.pat || auth.isDemo) {
      loadDemoData();
    } else {
      syncWithGitHub(false);
    }

    // Live real-time cooldown countdown ticker (every 10s)
    setInterval(updateCooldownDisplays, 10000);

    // Continuous auto-sync with GitHub every 15 seconds
    setInterval(() => {
      if (auth.pat && !auth.isDemo && !isSyncing) {
        syncWithGitHub(false);
      }
    }, 15000);

    // Instant auto-sync whenever the user switches back to the tab or focuses window
    window.addEventListener('focus', () => {
      if (auth.pat && !auth.isDemo && !isSyncing) {
        syncWithGitHub(false);
      }
    });

    document.addEventListener('visibilitychange', () => {
      if (!document.hidden && auth.pat && !auth.isDemo && !isSyncing) {
        syncWithGitHub(false);
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', startApp);
  } else {
    startApp();
  }

})();
