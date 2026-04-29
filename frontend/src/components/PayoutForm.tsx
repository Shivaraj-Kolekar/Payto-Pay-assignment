import { useState } from "react";
import client from "../api/client";

interface BankAccount {
  id: number;
  account_number: string;
  ifsc_code: string;
  account_holder_name: string;
}

interface PayoutFormProps {
  bankAccounts: BankAccount[];
  onPayoutCreated: () => void;
}

export default function PayoutForm({ bankAccounts, onPayoutCreated }: PayoutFormProps) {
  const [amount, setAmount] = useState("");
  const [bankAccountId, setBankAccountId] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    if (!amount || !bankAccountId) {
      setError("Please fill in all fields");
      return;
    }

    const amountPaise = Math.round(parseFloat(amount) * 100);
    if (amountPaise <= 0) {
      setError("Amount must be greater than 0");
      return;
    }

    setLoading(true);

    try {
      const idempotencyKey = crypto.randomUUID();
      await client.post(
        "/api/v1/payouts/",
        { amount_paise: amountPaise, bank_account_id: parseInt(bankAccountId) },
        { headers: { "Idempotency-Key": idempotencyKey } }
      );
      setSuccess("Payout request created");
      setAmount("");
      setBankAccountId("");
      onPayoutCreated();
    } catch {
      setError("Failed to create payout. Try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5">
      <div className="flex items-center gap-2.5 mb-5">
        <div className="w-8 h-8 rounded-lg bg-emerald-500/10 flex items-center justify-center">
          <svg className="w-4 h-4 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <h2 className="text-sm font-medium text-white">Create Payout</h2>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="bankAccount" className="block text-xs font-medium text-zinc-400 mb-1.5">
            Bank Account
          </label>
          <select
            id="bankAccount"
            value={bankAccountId}
            onChange={(e) => setBankAccountId(e.target.value)}
            required
            className="w-full px-3 py-2.5 bg-zinc-950 border border-zinc-700 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500/50 transition-all appearance-none cursor-pointer"
          >
            <option value="" disabled>Select account</option>
            {bankAccounts.map((account) => (
              <option key={account.id} value={account.id}>
                {account.account_holder_name} — {account.account_number}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="amount" className="block text-xs font-medium text-zinc-400 mb-1.5">
            Amount (₹)
          </label>
          <input
            id="amount"
            type="number"
            step="0.01"
            min="0.01"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            required
            placeholder="0.00"
            className="w-full px-3 py-2.5 bg-zinc-950 border border-zinc-700 rounded-lg text-white text-sm placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500/50 transition-all"
          />
        </div>

        {error && (
          <div className="bg-red-500/10 border border-red-500/30 text-red-400 text-xs px-3 py-2.5 rounded-lg">
            {error}
          </div>
        )}

        {success && (
          <div className="bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs px-3 py-2.5 rounded-lg">
            {success}
          </div>
        )}

        <button
          type="submit"
          disabled={loading || bankAccounts.length === 0}
          className="w-full py-2.5 px-4 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg transition-all duration-200 cursor-pointer"
        >
          {loading ? "Processing..." : "Create Payout"}
        </button>
      </form>

      {bankAccounts.length === 0 && (
        <p className="text-xs text-zinc-500 mt-3 text-center">
          No bank accounts added yet
        </p>
      )}
    </div>
  );
}
