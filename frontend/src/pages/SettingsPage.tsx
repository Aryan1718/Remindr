import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { PageContainer } from "@/components/layout/PageContainer";
import { SettingsSection, ToggleRow } from "@/components/settings/SettingsBits";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { useSaveSettingsMutation } from "@/features/settings/mutations";
import { useSettingsQuery } from "@/features/settings/queries";
import type { ProfileSettings } from "@/types/domain";

const settingsSchema = z.object({
  name: z.string().min(1),
  timezone: z.string().min(1),
  role: z.string().min(1),
  decisionStyle: z.enum(["Direct recommendation", "Ranked options"]),
  fatiguePreference: z.enum(["Daily", "Only when needed", "Manual only"]),
  explanationDepth: z.enum(["Brief", "Balanced", "Detailed"]),
  suggestionFrequency: z.enum(["Low", "Balanced", "High"]),
  reminderStyle: z.enum(["Gentle", "Direct", "Escalating"]),
  quietHours: z.object({
    start: z.string().min(1),
    end: z.string().min(1),
  }),
});

export function SettingsPage() {
  const { data } = useSettingsQuery();
  const mutation = useSaveSettingsMutation();
  const form = useForm<ProfileSettings>({
    resolver: zodResolver(settingsSchema),
    values: data,
  });

  useEffect(() => {
    if (data) form.reset(data);
  }, [data, form]);

  if (!data) {
    return (
      <PageContainer title="Settings" description="Control preferences without turning the app into an admin panel." />
    );
  }

  return (
    <PageContainer
      title="Settings"
      description="Preference controls stay narrow and readable so the assistant can remain proactive without feeling intrusive."
      actions={
        <Button onClick={form.handleSubmit((values) => mutation.mutate(values))} type="button">
          Save changes
        </Button>
      }
    >
      <div className="grid gap-6 lg:grid-cols-2">
        <SettingsSection title="Profile" description="Basic identity and context used for scheduling and tone.">
          <div className="grid gap-4 md:grid-cols-2">
            <Input {...form.register("name")} placeholder="Name" />
            <Input {...form.register("timezone")} placeholder="Timezone" />
            <Input {...form.register("role")} className="md:col-span-2" placeholder="Role" />
          </div>
        </SettingsSection>

        <SettingsSection title="Decision preferences" description="Control how assertive and explanatory the assistant feels.">
          <Select {...form.register("decisionStyle")}>
            <option>Direct recommendation</option>
            <option>Ranked options</option>
          </Select>
          <Select {...form.register("fatiguePreference")}>
            <option>Daily</option>
            <option>Only when needed</option>
            <option>Manual only</option>
          </Select>
          <Select {...form.register("explanationDepth")}>
            <option>Brief</option>
            <option>Balanced</option>
            <option>Detailed</option>
          </Select>
        </SettingsSection>

        <SettingsSection title="Notifications" description="Suggestion frequency, reminder tone, and quiet hours.">
          <Select {...form.register("suggestionFrequency")}>
            <option>Low</option>
            <option>Balanced</option>
            <option>High</option>
          </Select>
          <Select {...form.register("reminderStyle")}>
            <option>Gentle</option>
            <option>Direct</option>
            <option>Escalating</option>
          </Select>
          <div className="grid gap-4 md:grid-cols-2">
            <Input type="time" {...form.register("quietHours.start")} />
            <Input type="time" {...form.register("quietHours.end")} />
          </div>
        </SettingsSection>

        <SettingsSection title="Data and privacy" description="Review connector scope and retained memory controls.">
          <ToggleRow label="Memory visibility" description="Let the user inspect what reusable context is currently retained." />
          <ToggleRow label="Connector permissions" description="Make connector scope obvious without exposing raw auth details." />
          <div className="rounded-panel border border-[#5a3029] bg-[#271816] p-4">
            <p className="text-sm font-semibold text-danger">Danger zone</p>
            <p className="mt-2 text-sm text-muted">Delete data controls stay visible but intentionally hard to trigger.</p>
          </div>
        </SettingsSection>
      </div>
    </PageContainer>
  );
}
