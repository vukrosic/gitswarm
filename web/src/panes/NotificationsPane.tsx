import type { GitHubNotification } from '../types';
import { ago } from '../lib/time';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { PaneHeader, PaneShell } from './_shared';

interface NotificationsPaneProps {
  notifications: GitHubNotification[];
  loading: boolean;
  onRefresh: () => void;
}

const REASON_LABELS: Record<string, string> = {
  author: 'You authored',
  assign: 'You were assigned',
  comment: 'You commented',
  ci_activity: 'CI activity',
  invitation: 'Invitation',
  manual: 'Manual',
  mention: 'You were mentioned',
  review_requested: 'Review requested',
  security_alert: 'Security alert',
  state_change: 'State changed',
  subscribed: 'Subscribed',
  team_mention: 'Team mention',
};

const SUBJECT_ICON: Record<string, string> = {
  Issue: 'issue',
  PullRequest: 'pr',
  Release: 'release',
  Discussion: 'discussion',
  Commit: 'commit',
  CheckSuite: 'check',
};

function reasonLabel(reason: string): string {
  return REASON_LABELS[reason] || reason;
}

function notifTone(notif: GitHubNotification): 'default' | 'warning' | 'success' | 'destructive' | 'muted' {
  if (!notif.unread) return 'muted';
  if (notif.reason === 'security_alert') return 'destructive';
  if (notif.reason === 'review_requested') return 'warning';
  if (notif.reason === 'mention' || notif.reason === 'team_mention') return 'warning';
  return 'default';
}

export function NotificationsPane({ notifications, loading, onRefresh }: NotificationsPaneProps) {
  const unread = notifications.filter((n) => n.unread);
  const read = notifications.filter((n) => !n.unread);

  return (
    <PaneShell>
      <PaneHeader
        eyebrow="GitHub"
        title="Notifications"
        meta={`${unread.length} unread · ${read.length} read`}
        actions={
          <>
            <Button variant="outline" size="sm" onClick={onRefresh} disabled={loading}>
              Refresh
            </Button>
          </>
        }
      />

      {loading && !notifications.length ? (
        <div className="rounded-2xl border border-dashed border-border/70 bg-background/40 p-4 text-sm text-muted-foreground">
          Loading notifications…
        </div>
      ) : null}

      {!loading && !notifications.length ? (
        <div className="rounded-2xl border border-dashed border-border/70 bg-background/40 p-4 text-sm text-muted-foreground">
          No notifications. You're all caught up.
        </div>
      ) : null}

      {unread.length > 0 ? (
        <div className="space-y-2.5">
          <div className="text-[10px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
            Unread ({unread.length})
          </div>
          {unread.map((notif) => (
            <NotifCard key={notif.id} notif={notif} />
          ))}
        </div>
      ) : null}

      {read.length > 0 ? (
        <div className="space-y-2.5">
          <div className="text-[10px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
            Previously seen ({read.length})
          </div>
          {read.map((notif) => (
            <NotifCard key={notif.id} notif={notif} />
          ))}
        </div>
      ) : null}
    </PaneShell>
  );
}

function NotifCard({ notif }: { notif: GitHubNotification }) {
  const tone = notifTone(notif);

  function openOnGitHub() {
    if (!notif.subject_url) return;
    // Convert API URL to web URL
    let webUrl = notif.subject_url
      .replace('api.github.com/repos', 'github.com')
      .replace('/pulls/', '/pull/')
      .replace('/issues/', '/issues/');
    window.open(webUrl, '_blank', 'noopener,noreferrer');
  }

  return (
    <article
      className={`min-w-0 rounded-2xl border p-4 transition-all ${
        notif.unread
          ? 'border-primary/40 bg-primary/5 hover:border-primary/60'
          : 'border-border/70 bg-background/60'
      }`}
    >
      <div className="mb-2 flex flex-wrap items-start justify-between gap-2">
        <div className="flex min-w-0 items-center gap-2">
          <span
            className={`h-2 w-2 shrink-0 rounded-full ${
              notif.unread ? 'bg-primary' : 'bg-muted-foreground/30'
            }`}
          />
          <div className="min-w-0">
            <div className="truncate text-[13px] font-medium text-foreground" title={notif.subject_title}>
              {notif.subject_title || <span className="text-muted-foreground italic">no subject</span>}
            </div>
            <div className="mt-0.5 flex flex-wrap items-center gap-1.5 text-[11px] text-muted-foreground">
              <Badge
                variant={
                  notif.reason === 'security_alert'
                    ? 'destructive'
                    : notif.reason === 'review_requested'
                      ? 'warning'
                      : 'default'
                }
                className="text-[10px]"
              >
                {reasonLabel(notif.reason)}
              </Badge>
              {notif.repository_name ? (
                <span className="truncate">{notif.repository_name}</span>
              ) : null}
            </div>
          </div>
        </div>
        <div className="shrink-0 text-right text-[11px] text-muted-foreground">
          <div>{notif.updated_at ? ago(new Date(notif.updated_at).getTime() / 1000) : ''}</div>
          <div className="mt-0.5 capitalize">{notif.subject_type?.toLowerCase() || 'notification'}</div>
        </div>
      </div>
      {notif.subject_url ? (
        <button
          type="button"
          onClick={openOnGitHub}
          className="mt-2 text-[11px] text-primary hover:underline"
        >
          Open on GitHub →
        </button>
      ) : null}
    </article>
  );
}