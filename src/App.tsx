import React, { useState } from 'react';

// Knowledge base compiled from data/policies/*.md
interface PolicyChunk {
  file: string;
  section: string;
  keywords: string[];
  content: string;
}

const POLICY_CHUNKS: PolicyChunk[] = [
  {
    file: 'leave_policy.md',
    section: 'Parental and Family Leave',
    keywords: ['parental', 'maternity', 'paternity', 'baby', 'child', 'birth', 'adoption', 'caregiver', 'leave', 'days', 'weeks'],
    content: 'Primary caregivers are entitled to 26 weeks of fully paid parental leave (100% of base salary). Secondary caregivers (non-primary / partner) are entitled to 6 weeks of fully paid parental leave. Employees become eligible after 6 months of continuous service, and leave must be taken within the first 12 months following birth, adoption, or foster placement.'
  },
  {
    file: 'leave_policy.md',
    section: 'Annual Leave',
    keywords: ['annual', 'vacation', 'pto', 'holiday', 'rollover', 'accrual', 'days off'],
    content: 'All full-time employees are entitled to 25 paid vacation days per calendar year, accruing monthly at 2.08 days per month. Up to 5 unused annual leave days may be rolled over into the following calendar year, expiring on March 31st.'
  },
  {
    file: 'leave_policy.md',
    section: 'Sick and Medical Leave',
    keywords: ['sick', 'doctor', 'medical', 'illness', 'certificate', 'hospital', 'health'],
    content: 'Employees receive 12 paid sick days per calendar year. A written medical certificate from a licensed physician is required for any absence exceeding 3 consecutive business days. Unused sick leave does not roll over.'
  },
  {
    file: 'leave_policy.md',
    section: 'Bereavement Leave',
    keywords: ['bereavement', 'death', 'funeral', 'loss', 'compassionate', 'family member'],
    content: 'Employees are granted 5 consecutive paid business days for the loss of immediate family members (spouse, partner, child, parent, sibling) and 3 paid business days for extended family members (grandparents, aunts, uncles, in-laws).'
  },
  {
    file: 'leave_policy.md',
    section: 'Public Holidays and Floating Holidays',
    keywords: ['holiday', 'public holidays', 'floating', 'calendar', 'observance', 'off'],
    content: 'The company observes 11 designated official public holidays each year. In addition, every employee receives 2 paid floating holidays per year on January 1st for personal, cultural, or religious observances.'
  },
  {
    file: 'leave_policy.md',
    section: 'Unpaid Leave and Sabbaticals',
    keywords: ['sabbatical', 'unpaid', 'career break', 'extended leave', 'personal development'],
    content: 'Employees with at least 3 years of continuous tenure may apply for an unpaid sabbatical between 1 month and 6 months in duration, with health benefits subsidized for up to 3 months.'
  },
  {
    file: 'security_guidelines.md',
    section: 'Password and Authentication Security',
    keywords: ['password', 'auth', 'mfa', '2fa', 'authentication', 'length', 'lock', 'totp', 'fido2'],
    content: 'Passwords must be a minimum of 16 characters in length and include uppercase, lowercase, numbers, and symbols. Passwords must not match any of the previous 10 passwords. MFA via hardware keys or TOTP authenticator apps is mandatory (SMS MFA is prohibited). Sessions lock after 15 minutes of inactivity.'
  },
  {
    file: 'security_guidelines.md',
    section: 'Device and Endpoint Protection',
    keywords: ['laptop', 'device', 'encryption', 'filevault', 'bitlocker', 'edr', 'usb', 'stolen', 'lost'],
    content: 'All company laptops must have Full Disk Encryption (FileVault / BitLocker 256-bit AES) enabled. Endpoint Detection and Response (EDR) software must run 24/7. Removable USB drives are blocked. Lost or stolen hardware must be reported to SecOps within 1 hour.'
  },
  {
    file: 'security_guidelines.md',
    section: 'Remote Work and Wi-Fi Standards',
    keywords: ['remote', 'wifi', 'wi-fi', 'vpn', 'travel', 'public', 'privacy filter', 'wireguard'],
    content: 'All remote connections must use the corporate Zero-Trust Network Access or WireGuard VPN tunnel. Connecting via untrusted public Wi-Fi without VPN is prohibited. Physical privacy screen filters are mandatory in public spaces.'
  },
  {
    file: 'security_guidelines.md',
    section: 'Incident Response and Phishing Reporting',
    keywords: ['phishing', 'incident', 'report', 'breach', 'scam', 'hack', 'ransomware', 'emergency'],
    content: 'Suspicious emails must be reported within 30 minutes using the "Report Phishing" button or to abuse@company.internal. Severity-1 incidents trigger response pager within 15 minutes with hourly executive status updates.'
  },
  {
    file: 'hr_procedures.md',
    section: 'Expense Reimbursement and Per Diems',
    keywords: ['expense', 'reimbursement', 'per diem', 'food', 'meal', 'travel', 'receipt', 'mileage'],
    content: 'Expense reports must be submitted within 30 days. Receipts are mandatory for items over $25. Standard domestic meal per diem is capped at $75 per day ($20 breakfast, $25 lunch, $30 dinner). High-cost cities (NYC, SF, London, Tokyo) are capped at $100 per day. Mileage is reimbursed at $0.67/mile.'
  },
  {
    file: 'hr_procedures.md',
    section: 'Working Hours and Core Collaboration',
    keywords: ['working hours', 'core hours', 'schedule', 'overtime', 'remote hours', 'flexibility'],
    content: 'Standard schedule is 40 hours per week. Core collaboration hours are 10:00 AM to 3:00 PM local time. Flexible hours between 7:00 AM and 7:00 PM are permitted with manager agreement. Overtime for non-exempt staff is paid at 1.5x.'
  },
  {
    file: 'hr_procedures.md',
    section: 'Professional Development and Tuition Assistance',
    keywords: ['tuition', 'stipend', 'learning', 'education', 'course', 'degree', 'training', 'books'],
    content: 'Full-time employees after 90 days receive an annual individual learning stipend of $2,500 for books, conferences, and certifications. Tuition assistance up to $5,000 per calendar year is available for accredited degrees with a grade of B (3.0 GPA) or higher.'
  },
  {
    file: 'hr_procedures.md',
    section: 'Performance Reviews and Promotion Cycles',
    keywords: ['performance', 'review', 'promotion', 'raise', 'mid-year', 'annual', 'evaluation', 'pip'],
    content: 'Formal performance reviews occur twice annually in June (Mid-Year) and December (Annual). Compensation adjustments take effect February 1st and August 1st. Performance Improvement Plans (PIPs) run on a 60-day cycle.'
  }
];

function answerPolicyQuery(query: string): { answer: string; source: string; confidence: number } {
  const normalized = query.toLowerCase().trim();
  if (!normalized) {
    return {
      answer: 'Please enter a question to search company policies.',
      source: '',
      confidence: 0
    };
  }

  const queryTerms = normalized
    .replace(/[^\w\s]/g, ' ')
    .split(/\s+/)
    .filter((t) => t.length > 2);

  let bestChunk: PolicyChunk | null = null;
  let highestScore = 0;

  for (const chunk of POLICY_CHUNKS) {
    let score = 0;
    const sectionLower = chunk.section.toLowerCase();
    const contentLower = chunk.content.toLowerCase();

    for (const term of queryTerms) {
      if (chunk.keywords.some((kw) => kw.includes(term) || term.includes(kw))) {
        score += 5;
      }
      if (sectionLower.includes(term)) {
        score += 4;
      }
      if (contentLower.includes(term)) {
        score += 2;
      }
    }

    if (score > highestScore) {
      highestScore = score;
      bestChunk = chunk;
    }
  }

  if (!bestChunk || highestScore < 2) {
    return {
      answer: 'I could not find the answer in the provided company policy documentation. Please confirm with HR or People Operations.',
      source: 'Internal Policies',
      confidence: 0
    };
  }

  return {
    answer: `${bestChunk.content} [1]`,
    source: `${bestChunk.file} > ${bestChunk.section}`,
    confidence: Math.min(100, Math.round(highestScore * 10))
  };
}

export default function App() {
  const [query, setQuery] = useState('How many days of parental leave are allowed?');
  const [result, setResult] = useState(() => answerPolicyQuery('How many days of parental leave are allowed?'));

  const handleSearch = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setResult(answerPolicyQuery(query));
  };

  const handleQuickPrompt = (sampleText: string) => {
    setQuery(sampleText);
    setResult(answerPolicyQuery(sampleText));
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 flex flex-col items-center justify-start p-6 sm:p-12 font-sans">
      <div className="w-full max-w-2xl bg-white rounded-xl shadow-md border border-slate-200 p-6 sm:p-8 space-y-6">
        
        {/* Enter Prompt Header */}
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900">
            Enter Prompt: Policy RAG Assistant
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Answers questions about leave policies, security guidelines, and HR procedures from verified company documentation.
          </p>
        </div>

        {/* Input box for Query */}
        <form onSubmit={handleSearch} className="space-y-3">
          <label htmlFor="policy-query" className="block text-sm font-semibold text-slate-700">
            Query:
          </label>
          <div className="flex gap-2">
            <input
              id="policy-query"
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g. How many days of parental leave are allowed?"
              className="flex-1 px-4 py-2.5 rounded-lg border border-slate-300 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm shadow-xs"
            />
            <button
              type="submit"
              className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white font-medium rounded-lg text-sm transition-colors cursor-pointer shadow-xs"
            >
              Ask
            </button>
          </div>
        </form>

        {/* Quick Suggestion Chips */}
        <div className="space-y-1.5">
          <span className="text-xs font-medium text-slate-500">Suggested queries:</span>
          <div className="flex flex-wrap gap-2">
            {[
              'How many days of parental leave are allowed?',
              'What is the minimum password length?',
              'What is the daily meal per diem for New York?',
              'How many sick days per year?'
            ].map((promptText) => (
              <button
                key={promptText}
                type="button"
                onClick={() => handleQuickPrompt(promptText)}
                className="text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 px-3 py-1.5 rounded-full transition-colors cursor-pointer text-left"
              >
                {promptText}
              </button>
            ))}
          </div>
        </div>

        {/* Paragraph to get Result */}
        <div className="border-t border-slate-100 pt-5 space-y-2">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500">Result</h2>
            {result.source && (
              <span className="text-xs font-medium text-blue-700 bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
                [1] {result.source}
              </span>
            )}
          </div>
          <p className="text-base text-slate-800 bg-slate-50 p-4 rounded-lg border border-slate-200 leading-relaxed">
            {result.answer}
          </p>
        </div>

      </div>
    </div>
  );
}
