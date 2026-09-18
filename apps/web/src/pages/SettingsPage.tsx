import { Pencil, Plus, Trash2 } from "lucide-react";
import { useState, type FormEvent } from "react";

import { useAIUsage, useCategories, useCreateCategory, useDeleteAccount, useDeleteCategory, useUpdateCategory, useUpdateProfile } from "@/api/hooks";
import { Alert, Badge, Button, Card, Dialog, Field, Input, Spinner } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Category } from "@/types";

export function SettingsPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
      <div className="grid gap-4 lg:grid-cols-2">
        <ProfileCard />
        <AIUsageCard />
        <div className="lg:col-span-2">
          <CategoriesCard />
        </div>
        <div className="lg:col-span-2">
          <DangerZone />
        </div>
      </div>
    </div>
  );
}

function message(err: unknown, fallback: string): string {
  return err instanceof ApiError ? err.message : fallback;
}

function ProfileCard() {
  const { user, refreshUser } = useAuth();
  const update = useUpdateProfile();
  const [name, setName] = useState(user?.name ?? "");
  const [currency, setCurrency] = useState(user?.default_currency ?? "EUR");
  const [saved, setSaved] = useState(false);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    update.mutate(
      { name: name.trim(), default_currency: currency.trim().toUpperCase() },
      {
        onSuccess: async () => {
          await refreshUser();
          setSaved(true);
        },
      },
    );
  };

  return (
    <Card title="Profile">
      <form onSubmit={submit} className="space-y-3">
        {update.isError && <Alert>{message(update.error, "Could not save")}</Alert>}
        {saved && !update.isError && <Alert kind="success">Profile saved.</Alert>}
        <Field label="Email" htmlFor="profile-email">
          <Input id="profile-email" value={user?.email ?? ""} disabled />
        </Field>
        <Field label="Name" htmlFor="profile-name">
          <Input id="profile-name" value={name} onChange={(e) => setName(e.target.value)} required maxLength={120} />
        </Field>
        <Field label="Default currency" htmlFor="profile-currency" hint="ISO code, e.g. EUR or CHF">
          <Input id="profile-currency" value={currency} onChange={(e) => setCurrency(e.target.value)} maxLength={3} minLength={3} required />
        </Field>
        <Button type="submit" loading={update.isPending}>
          Save
        </Button>
      </form>
    </Card>
  );
}

function AIUsageCard() {
  const usage = useAIUsage();
  return (
    <Card title="AI usage">
      {usage.isLoading ? (
        <Spinner />
      ) : usage.data ? (
        <dl className="grid grid-cols-2 gap-3 text-sm">
          <div>
            <dt className="text-slate-500">Model calls</dt>
            <dd className="text-xl font-semibold tabular-nums">{usage.data.calls}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Tokens (in / out)</dt>
            <dd className="text-xl font-semibold tabular-nums">
              {usage.data.input_tokens.toLocaleString()} / {usage.data.output_tokens.toLocaleString()}
            </dd>
          </div>
          {Object.entries(usage.data.by_kind).map(([kind, count]) => (
            <div key={kind}>
              <dt className="text-slate-500">{kind.replace("_", " ")}</dt>
              <dd className="font-medium tabular-nums">{count}</dd>
            </div>
          ))}
        </dl>
      ) : (
        <Alert>Could not load usage.</Alert>
      )}
      <p className="mt-3 text-xs text-slate-500">
        Receipts and questions are processed by the configured AI provider. Token counts let you estimate cost.
      </p>
    </Card>
  );
}

function CategoriesCard() {
  const categories = useCategories();
  const create = useCreateCategory();
  const update = useUpdateCategory();
  const remove = useDeleteCategory();
  const [editing, setEditing] = useState<Category | "new" | null>(null);
  const [name, setName] = useState("");
  const [color, setColor] = useState("#2a78d6");
  const [error, setError] = useState<string | null>(null);

  const open = (target: Category | "new") => {
    setEditing(target);
    setName(target === "new" ? "" : target.name);
    setColor(target === "new" ? "#2a78d6" : target.color);
    setError(null);
  };

  const submit = (event: FormEvent) => {
    event.preventDefault();
    const done = { onSuccess: () => setEditing(null), onError: (err: unknown) => setError(message(err, "Could not save")) };
    if (editing === "new") create.mutate({ name: name.trim(), color }, done);
    else if (editing) update.mutate({ id: editing.id, name: name.trim(), color }, done);
  };

  return (
    <Card
      title="Categories"
      action={
        <Button size="sm" variant="secondary" onClick={() => open("new")}>
          <Plus className="h-4 w-4" aria-hidden /> New
        </Button>
      }
    >
      {remove.isError && <div className="mb-3"><Alert>{message(remove.error, "Could not delete")}</Alert></div>}
      {categories.isLoading ? (
        <Spinner />
      ) : (
        <ul className="flex flex-wrap gap-2">
          {categories.data?.map((c) => (
            <li key={c.id} className="flex items-center gap-1 rounded-full border border-slate-200 bg-white pl-1 pr-1">
              <Badge color={c.color} className="border-0 bg-transparent">
                {c.name}
              </Badge>
              <button className="rounded-full p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700" onClick={() => open(c)} aria-label={`Edit ${c.name}`}>
                <Pencil className="h-3 w-3" />
              </button>
              <button
                className="rounded-full p-1 text-slate-400 hover:bg-red-50 hover:text-red-600"
                onClick={() => window.confirm(`Delete "${c.name}"? Expenses keep existing without a category.`) && remove.mutate(c.id)}
                aria-label={`Delete ${c.name}`}
              >
                <Trash2 className="h-3 w-3" />
              </button>
            </li>
          ))}
        </ul>
      )}
      <Dialog open={editing !== null} title={editing === "new" ? "New category" : "Edit category"} onClose={() => setEditing(null)}>
        <form onSubmit={submit} className="space-y-3">
          {error && <Alert>{error}</Alert>}
          <Field label="Name" htmlFor="cat-name">
            <Input id="cat-name" value={name} onChange={(e) => setName(e.target.value)} required maxLength={80} autoFocus />
          </Field>
          <Field label="Colour" htmlFor="cat-color">
            <input id="cat-color" type="color" value={color} onChange={(e) => setColor(e.target.value)} className="h-10 w-16 cursor-pointer rounded border border-slate-300" />
          </Field>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="secondary" onClick={() => setEditing(null)}>
              Cancel
            </Button>
            <Button type="submit" loading={create.isPending || update.isPending}>
              Save
            </Button>
          </div>
        </form>
      </Dialog>
    </Card>
  );
}

function DangerZone() {
  const { logout } = useAuth();
  const deleteAccount = useDeleteAccount();
  const [password, setPassword] = useState("");
  const [open, setOpen] = useState(false);

  return (
    <Card title="Danger zone">
      <p className="text-sm text-slate-600">
        Deleting your account permanently removes all expenses, receipts and uploaded files. This cannot be undone.
      </p>
      <Button variant="danger" className="mt-3" onClick={() => setOpen(true)}>
        Delete account
      </Button>
      <Dialog open={open} title="Delete account" onClose={() => setOpen(false)}>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            deleteAccount.mutate(password, { onSuccess: () => logout() });
          }}
          className="space-y-3"
        >
          {deleteAccount.isError && <Alert>{message(deleteAccount.error, "Could not delete account")}</Alert>}
          <Field label="Confirm with your password" htmlFor="delete-password">
            <Input id="delete-password" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </Field>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="secondary" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="danger" loading={deleteAccount.isPending}>
              Delete everything
            </Button>
          </div>
        </form>
      </Dialog>
    </Card>
  );
}
