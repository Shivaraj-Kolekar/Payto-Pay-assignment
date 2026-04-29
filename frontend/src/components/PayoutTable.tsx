interface Payout {
  id: number;
  amount_paise: number;
  status: string;
  bank_account: number;
  bank_account_name: string;
  created_at: string;
}

interface PayoutTableProps {
  payouts: Payout[];
}

const statusStyles: Record<string, string> = {
  pending: 'bg-yellow-500/10 text-yellow-400',
  processing: 'bg-blue-500/10 text-blue-400',
  completed: 'bg-emerald-500/10 text-emerald-400',
  failed: 'bg-red-500/10 text-red-400',
};

export default function PayoutTable({ payouts }: PayoutTableProps) {
  const formatRupees = (paise: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
    }).format(paise / 100);
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString('en-IN', {
      dateStyle: 'medium',
      timeStyle: 'short',
    });
  };

  if (payouts.length === 0) {
    return (
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-8 text-center">
        <p className="text-sm text-zinc-500">No payouts yet</p>
      </div>
    );
  }

  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden">
      <div className="px-5 py-3.5 border-b border-zinc-800">
        <h2 className="text-sm font-medium text-white">Payout History</h2>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-zinc-800">
              <th className="text-left text-xs font-medium text-zinc-500 px-5 py-2.5">ID</th>
              <th className="text-left text-xs font-medium text-zinc-500 px-5 py-2.5">Amount</th>
              <th className="text-left text-xs font-medium text-zinc-500 px-5 py-2.5">Status</th>
              <th className="text-left text-xs font-medium text-zinc-500 px-5 py-2.5">Account</th>
              <th className="text-left text-xs font-medium text-zinc-500 px-5 py-2.5">Date</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-800">
            {payouts.map((payout) => (
              <tr key={payout.id} className="hover:bg-zinc-800/30 transition-colors">
                <td className="px-5 py-3 text-xs text-zinc-400 font-mono">#{payout.id}</td>
                <td className="px-5 py-3 text-sm text-white font-medium">{formatRupees(payout.amount_paise)}</td>
                <td className="px-5 py-3">
                  <span className={`inline-flex px-2 py-0.5 text-xs font-medium rounded-md ${statusStyles[payout.status] || 'bg-zinc-500/10 text-zinc-400'}`}>
                    {payout.status}
                  </span>
                </td>
                <td className="px-5 py-3 text-xs text-zinc-500">{payout.bank_account_name}</td>
                <td className="px-5 py-3 text-xs text-zinc-500">{formatDate(payout.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
