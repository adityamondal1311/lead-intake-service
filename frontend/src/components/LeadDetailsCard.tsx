import type { ReactNode } from 'react'

import type { LeadDetail } from '../api/types'
import { formatDateTime } from '../lib/format'

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="grid grid-cols-3 gap-3 py-2 text-sm">
      <dt className="text-zinc-500">{label}</dt>
      <dd className="col-span-2 min-w-0 break-words text-zinc-900">{children}</dd>
    </div>
  )
}

const missing = <span className="text-zinc-400">—</span>

/** A reference id: small, muted, monospace; the full value is selectable and in the tooltip. */
function Reference({ value }: { value: string }) {
  return (
    <code title={value} className="block truncate font-mono text-xs text-zinc-500 select-all">
      {value}
    </code>
  )
}

export default function LeadDetailsCard({ lead }: { lead: LeadDetail }) {
  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-5">
      <section aria-labelledby="contact-heading">
        <h2 id="contact-heading" className="text-sm font-semibold text-zinc-900">
          Contact
        </h2>
        <dl className="mt-1 divide-y divide-zinc-100">
          <Field label="Email">
            {lead.email ? (
              <a href={`mailto:${lead.email}`} className="text-accent-700 hover:underline">
                {lead.email}
              </a>
            ) : (
              missing
            )}
          </Field>
          <Field label="Phone">
            {lead.phone ? (
              <a href={`tel:${lead.phone}`} className="text-accent-700 hover:underline">
                {lead.phone}
              </a>
            ) : (
              missing
            )}
          </Field>
        </dl>
      </section>

      <section aria-labelledby="campaign-heading" className="mt-5">
        <h2 id="campaign-heading" className="text-sm font-semibold text-zinc-900">
          Campaign
        </h2>
        <dl className="mt-1 divide-y divide-zinc-100">
          <Field label="Campaign">{lead.campaignId ?? missing}</Field>
          <Field label="Form">{lead.formId ?? missing}</Field>
          <Field label="Ad">{lead.adId ?? missing}</Field>
          <Field label="Submitted on Meta">
            {lead.metaCreatedAt ? formatDateTime(lead.metaCreatedAt) : missing}
          </Field>
        </dl>
      </section>

      <section aria-labelledby="reference-heading" className="mt-5">
        <h2 id="reference-heading" className="text-sm font-semibold text-zinc-900">
          Reference
        </h2>
        <dl className="mt-1 divide-y divide-zinc-100">
          <Field label="Meta lead ID">
            <Reference value={lead.externalId} />
          </Field>
          <Field label="Lead ID">
            <Reference value={lead.id} />
          </Field>
        </dl>
      </section>
    </div>
  )
}
