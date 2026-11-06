/**
 * Login right-panel backdrop: refined résumé “papers” + screening-themed accents.
 * No eyes / no plus — replaced with ranking, verification, and pipeline motifs.
 */
export function LoginWatermark() {
  return (
    <div
      aria-hidden
      className="pointer-events-none absolute inset-0 overflow-hidden bg-[#F8FAFC]"
      style={{ isolation: "isolate" }}
    >
      <svg
        className="absolute inset-0 h-full w-full"
        viewBox="0 0 1200 800"
        preserveAspectRatio="xMidYMid slice"
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          <linearGradient id="loginPaperWash" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#FFFFFF" stopOpacity="0.92" />
            <stop offset="100%" stopColor="#F1F5F9" stopOpacity="0.88" />
          </linearGradient>
          <linearGradient id="loginAccentBar" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#6366F1" stopOpacity="0.52" />
            <stop offset="100%" stopColor="#38BDF8" stopOpacity="0.42" />
          </linearGradient>
          <filter id="loginCardShadow" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="0" dy="4" stdDeviation="6" floodColor="#64748B" floodOpacity="0.2" />
          </filter>
          <radialGradient id="loginVignette" cx="50%" cy="44%" r="68%">
            <stop offset="0%" stopColor="#F8FAFC" stopOpacity="0" />
            <stop offset="55%" stopColor="#F8FAFC" stopOpacity="0" />
            <stop offset="100%" stopColor="#F8FAFC" stopOpacity="0.48" />
          </radialGradient>
        </defs>

        {/* Base wash */}
        <rect width="1200" height="800" fill="url(#loginPaperWash)" />
        <rect width="1200" height="800" fill="#F8FAFC" fillOpacity="0.35" />

        {/* --- Card A — top-left: profile + education + skill meters --- */}
        <g transform="rotate(-7 200 220)" opacity="0.55" filter="url(#loginCardShadow)">
          <rect x="36" y="48" width="248" height="318" rx="12" fill="white" stroke="#A8BFD9" strokeWidth="1.15" />
          <rect x="36" y="48" width="248" height="5" rx="12" fill="url(#loginAccentBar)" />
          <circle cx="88" cy="118" r="32" fill="#E0EAF5" stroke="#B8CEEA" strokeWidth="1" />
          <path
            d="M 88 102 c 8 0 14 6 14 14 s-6 14-14 14-14-6-14-14 6-14 14-14z"
            fill="#94A3B8"
            fillOpacity="0.35"
          />
          <rect x="132" y="96" width="132" height="10" rx="4" fill="#CBD5E1" fillOpacity="0.55" />
          <rect x="132" y="112" width="88" height="7" rx="3" fill="#E2E8F0" />
          <rect x="52" y="168" width="56" height="5" rx="2" fill="#6366F1" fillOpacity="0.5" />
          <text x="52" y="192" fontFamily="system-ui,sans-serif" fontSize="10" fontWeight="700" fill="#334155" letterSpacing="0.06em">
            EDUCATION
          </text>
          <rect x="52" y="200" width="188" height="6" rx="3" fill="#E2E8F0" />
          <rect x="52" y="212" width="156" height="6" rx="3" fill="#E2E8F0" />
          <rect x="52" y="232" width="48" height="5" rx="2" fill="#38BDF8" fillOpacity="0.45" />
          <text x="52" y="254" fontFamily="system-ui,sans-serif" fontSize="10" fontWeight="700" fill="#334155" letterSpacing="0.06em">
            SKILLS
          </text>
          {/* Skill bars */}
          <rect x="52" y="262" width="180" height="8" rx="4" fill="#EEF2F7" />
          <rect x="52" y="262" width="142" height="8" rx="4" fill="#6366F1" fillOpacity="0.48" />
          <rect x="52" y="278" width="180" height="8" rx="4" fill="#EEF2F7" />
          <rect x="52" y="278" width="118" height="8" rx="4" fill="#38BDF8" fillOpacity="0.52" />
          <rect x="52" y="294" width="180" height="8" rx="4" fill="#EEF2F7" />
          <rect x="52" y="294" width="96" height="8" rx="4" fill="#34D399" fillOpacity="0.48" />
          {/* Fit badge */}
          <rect x="210" y="248" width="58" height="22" rx="6" fill="#ECFDF5" stroke="#6EE7B7" strokeOpacity="0.6" strokeWidth="1" />
          <text x="239" y="263" textAnchor="middle" fontFamily="system-ui,sans-serif" fontSize="9" fontWeight="700" fill="#047857">
            Fit 94
          </text>
        </g>

        {/* --- Card B — bottom-left: experience timeline + tags --- */}
        <g transform="rotate(5 120 640)" opacity="0.5" filter="url(#loginCardShadow)">
          <rect x="4" y="520" width="228" height="278" rx="12" fill="white" stroke="#A8BFD9" strokeWidth="1.15" />
          <rect x="4" y="520" width="228" height="5" rx="12" fill="url(#loginAccentBar)" />
          <circle cx="52" cy="572" r="24" fill="#E0EAF5" stroke="#B8CEEA" strokeWidth="1" />
          <rect x="86" y="556" width="118" height="9" rx="3" fill="#CBD5E1" fillOpacity="0.6" />
          <rect x="86" y="570" width="72" height="6" rx="2" fill="#E2E8F0" />
          <text x="22" y="628" fontFamily="system-ui,sans-serif" fontSize="10" fontWeight="700" fill="#334155" letterSpacing="0.06em">
            EXPERIENCE
          </text>
          <circle cx="30" cy="648" r="4" fill="#6366F1" fillOpacity="0.45" />
          <rect x="42" y="642" width="170" height="6" rx="3" fill="#E2E8F0" />
          <rect x="42" y="654" width="140" height="6" rx="3" fill="#E2E8F0" />
          <circle cx="30" cy="684" r="4" fill="#94A3B8" fillOpacity="0.4" />
          <rect x="42" y="678" width="150" height="6" rx="3" fill="#E2E8F0" />
          <text x="22" y="722" fontFamily="system-ui,sans-serif" fontSize="10" fontWeight="700" fill="#334155" letterSpacing="0.06em">
            STACK
          </text>
          <rect x="22" y="730" width="52" height="18" rx="6" fill="#EEF2FF" stroke="#A5B4FC" strokeOpacity="0.5" strokeWidth="0.8" />
          <text x="48" y="742" textAnchor="middle" fontFamily="system-ui,sans-serif" fontSize="8" fontWeight="600" fill="#4F46E5">
            Python
          </text>
          <rect x="82" y="730" width="44" height="18" rx="6" fill="#F0FDF4" stroke="#86EFAC" strokeOpacity="0.5" strokeWidth="0.8" />
          <text x="104" y="742" textAnchor="middle" fontFamily="system-ui,sans-serif" fontSize="8" fontWeight="600" fill="#15803D">
            OSS
          </text>
          <rect x="134" y="730" width="56" height="18" rx="6" fill="#F8FAFC" stroke="#CBD5E1" strokeWidth="0.8" />
          <text x="162" y="742" textAnchor="middle" fontFamily="system-ui,sans-serif" fontSize="8" fontWeight="600" fill="#64748B">
            LangGraph
          </text>
        </g>

        {/* --- Card C — top-right: JD match summary --- */}
        <g transform="rotate(-4 1000 200)" opacity="0.52" filter="url(#loginCardShadow)">
          <rect x="888" y="44" width="242" height="302" rx="12" fill="white" stroke="#A8BFD9" strokeWidth="1.15" />
          <rect x="888" y="44" width="242" height="5" rx="12" fill="url(#loginAccentBar)" />
          <rect x="908" y="64" width="100" height="11" rx="4" fill="#CBD5E1" fillOpacity="0.55" />
          <rect x="1018" y="66" width="96" height="22" rx="8" fill="#FEF3C7" stroke="#FCD34D" strokeOpacity="0.5" strokeWidth="0.8" />
          <text x="1066" y="81" textAnchor="middle" fontFamily="system-ui,sans-serif" fontSize="9" fontWeight="700" fill="#B45309">
            JD match
          </text>
          <text x="908" y="118" fontFamily="system-ui,sans-serif" fontSize="10" fontWeight="700" fill="#334155" letterSpacing="0.06em">
            EXPERIENCE
          </text>
          <rect x="908" y="126" width="176" height="7" rx="3" fill="#E2E8F0" />
          <rect x="908" y="138" width="148" height="7" rx="3" fill="#E2E8F0" />
          <rect x="908" y="158" width="176" height="7" rx="3" fill="#E2E8F0" />
          <text x="908" y="188" fontFamily="system-ui,sans-serif" fontSize="10" fontWeight="700" fill="#334155" letterSpacing="0.06em">
            SKILLS
          </text>
          <rect x="908" y="196" width="80" height="16" rx="7" fill="#D0E2F5" fillOpacity="0.85" />
          <rect x="996" y="196" width="68" height="16" rx="7" fill="#E0E7FF" />
          <rect x="908" y="218" width="72" height="16" rx="7" fill="#E2E8F0" />
          <text x="908" y="258" fontFamily="system-ui,sans-serif" fontSize="10" fontWeight="700" fill="#334155" letterSpacing="0.06em">
            EDUCATION
          </text>
          <rect x="908" y="266" width="160" height="6" rx="3" fill="#E2E8F0" />
          <rect x="908" y="278" width="120" height="6" rx="3" fill="#E2E8F0" />
        </g>

        {/* --- Card D — bottom-right: condensed score strip --- */}
        <g transform="rotate(6 1000 640)" opacity="0.48" filter="url(#loginCardShadow)">
          <rect x="892" y="528" width="220" height="268" rx="12" fill="white" stroke="#A8BFD9" strokeWidth="1.15" />
          <rect x="892" y="528" width="220" height="5" rx="12" fill="url(#loginAccentBar)" />
          <circle cx="938" cy="576" r="22" fill="#E0EAF5" stroke="#B8CEEA" strokeWidth="1" />
          <rect x="972" y="562" width="120" height="8" rx="3" fill="#CBD5E1" fillOpacity="0.55" />
          <rect x="972" y="576" width="88" height="6" rx="2" fill="#E2E8F0" />
          <text x="912" y="624" fontFamily="system-ui,sans-serif" fontSize="10" fontWeight="700" fill="#334155" letterSpacing="0.06em">
            EDUCATION
          </text>
          <rect x="912" y="632" width="148" height="6" rx="3" fill="#E2E8F0" />
          <text x="912" y="668" fontFamily="system-ui,sans-serif" fontSize="10" fontWeight="700" fill="#334155" letterSpacing="0.06em">
            SKILLS
          </text>
          <rect x="912" y="676" width="188" height="7" rx="3" fill="#EEF2F7" />
          <rect x="912" y="676" width="152" height="7" rx="3" fill="#6366F1" fillOpacity="0.45" />
          <rect x="912" y="690" width="188" height="7" rx="3" fill="#EEF2F7" />
          <rect x="912" y="690" width="124" height="7" rx="3" fill="#38BDF8" fillOpacity="0.46" />
          <rect x="912" y="718" width="188" height="36" rx="8" fill="#F8FAFC" stroke="#E2E8F0" strokeWidth="1" />
          <text x="928" y="736" fontFamily="system-ui,sans-serif" fontSize="8" fontWeight="600" fill="#64748B">
            Rank
          </text>
          <text x="928" y="750" fontFamily="system-ui,sans-serif" fontSize="14" fontWeight="800" fill="#1E293B">
            #3
          </text>
          <text x="1020" y="742" fontFamily="system-ui,sans-serif" fontSize="9" fill="#64748B">
            of 120
          </text>
        </g>

        {/* --- Use-case icons — higher contrast for visibility --- */}

        {/* Shield + check — trusted screening */}
        <g transform="translate(620 120)" opacity="0.42">
          <path
            d="M 0 -28 L 26 -18 L 26 8 Q 26 28 0 42 Q -26 28 -26 8 L -26 -18 Z"
            fill="#E0E7FF"
            fillOpacity="0.95"
            stroke="#4F46E5"
            strokeOpacity="0.55"
            strokeWidth="1.75"
          />
          <path d="M -8 4 L -2 12 L 12 -6" fill="none" stroke="#059669" strokeOpacity="0.85" strokeWidth="2.75" strokeLinecap="round" strokeLinejoin="round" />
        </g>

        {/* Ranking bars — ordered evaluation */}
        <g transform="translate(280 120)" opacity="0.4">
          <rect x="0" y="18" width="10" height="28" rx="2" fill="#6366F1" fillOpacity="0.55" />
          <rect x="16" y="8" width="10" height="38" rx="2" fill="#6366F1" fillOpacity="0.72" />
          <rect x="32" y="0" width="10" height="46" rx="2" fill="#6366F1" fillOpacity="0.88" />
          <path d="M 21 -8 L 21 -2 M 18 -8 L 24 -8" stroke="#D97706" strokeOpacity="0.75" strokeWidth="1.75" strokeLinecap="round" />
        </g>

        {/* Mini pipeline — multi-step graph */}
        <g transform="translate(720 640)" opacity="0.4" fill="none" strokeLinecap="round">
          <path d="M 0 0 L 36 0 L 72 0 L 108 0" stroke="#475569" strokeOpacity="0.55" strokeWidth="1.75" />
          <circle cx="0" cy="0" r="6" fill="#E0E7FF" stroke="#4F46E5" strokeOpacity="0.65" strokeWidth="1.35" />
          <circle cx="36" cy="0" r="6" fill="#E0E7FF" stroke="#4F46E5" strokeOpacity="0.65" strokeWidth="1.35" />
          <circle cx="72" cy="0" r="6" fill="#E0F2FE" stroke="#0284C7" strokeOpacity="0.65" strokeWidth="1.35" />
          <circle cx="108" cy="0" r="7" fill="#ECFDF5" stroke="#059669" strokeOpacity="0.65" strokeWidth="1.35" />
          <path d="M 72 0 L 72 28 L 90 28" stroke="#64748B" strokeOpacity="0.5" strokeWidth="1.35" />
          <circle cx="102" cy="28" r="5" fill="#F1F5F9" stroke="#64748B" strokeOpacity="0.6" strokeWidth="1.1" />
        </g>

        {/* Magnifying glass over doc — research / evidence (abstract) */}
        <g transform="translate(480 680)" opacity="0.38">
          <rect x="-22" y="-18" width="36" height="44" rx="4" fill="white" fillOpacity="0.92" stroke="#94A3B8" strokeWidth="1.15" transform="rotate(-6)" />
          <circle cx="8" cy="-4" r="16" fill="none" stroke="#4F46E5" strokeOpacity="0.6" strokeWidth="2.75" />
          <line x1="18" y1="12" x2="32" y2="28" stroke="#4F46E5" strokeOpacity="0.6" strokeWidth="2.75" strokeLinecap="round" />
        </g>

        {/* Center readability — radial wash so the form stays legible */}
        <rect width="1200" height="800" fill="url(#loginVignette)" />
      </svg>
    </div>
  );
}
