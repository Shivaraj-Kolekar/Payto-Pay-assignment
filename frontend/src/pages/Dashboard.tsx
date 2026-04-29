import { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import client from "../api/client";
import BalanceCard from "../components/BalanceCard";
import PayoutForm from "../components/PayoutForm";
import PayoutTable from "../components/PayoutTable";

interface MerchantData {
  id: number;
  email: string;
  business_name: string;
  available_balance: number;
  held_balance: number;
}

interface BankAccount {
  id: number;
  account_number: string;
  ifsc_code: string;
  account_holder_name: string;
}

interface Payout {
  id: number;
  amount_paise: number;
  status: string;
  bank_account: number;
  bank_account_name: string;
  created_at: string;
}

export default function Dashboard() {
  const navigate = useNavigate();
  const [merchant, setMerchant] = useState<MerchantData | null>(null);
  const [bankAccounts, setBankAccounts] = useState<BankAccount[]>([]);
  const [payouts, setPayouts] = useState<Payout[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    try {
      const [merchantRes, payoutsRes, accountsRes] = await Promise.all([
        client.get("/api/v1/merchants/me/"),
        client.get("/api/v1/payouts/"),
        client.get("/api/v1/payouts/bank-accounts/"),
      ]);
      setMerchant(merchantRes.data);
      setPayouts(payoutsRes.data);
      setBankAccounts(accountsRes.data);
    } catch {
      // 401 interceptor will handle redirect
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();

    // Poll every 5 seconds for live updates
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    navigate("/login");
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
        <div className="flex items-center gap-2.5 text-zinc-500 text-sm">
          <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
              fill="none"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
            />
          </svg>
          Loading...
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-zinc-950">
      {/* Header */}
      <header className="border-b border-zinc-800 bg-zinc-950/80 backdrop-blur sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
              <svg
                className="w-4 h-4 text-emerald-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
            <div>
              <h1 className="text-sm font-medium text-white leading-none">
                {merchant?.business_name}
              </h1>
              <p className="text-xs text-zinc-500 mt-0.5">{merchant?.email}</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="hidden sm:flex items-center gap-1.5 text-xs text-emerald-400">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
              Live
            </div>
            <button
              onClick={handleLogout}
              className="text-xs text-zinc-500 hover:text-white px-2.5 py-1.5 rounded-lg hover:bg-zinc-800 transition-all cursor-pointer"
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-5xl mx-auto px-4 sm:px-6 py-6 space-y-5">
        {/* Balance Cards */}
        <BalanceCard
          availableBalance={merchant?.available_balance ?? 0}
          heldBalance={merchant?.held_balance ?? 0}
        />

        {/* Payout Form + Table */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          <div className="lg:col-span-1">
            <PayoutForm
              bankAccounts={bankAccounts}
              onPayoutCreated={fetchData}
            />
          </div>
          <div className="lg:col-span-2">
            <PayoutTable payouts={payouts} />
          </div>
        </div>
      </main>
    </div>
  );
}
