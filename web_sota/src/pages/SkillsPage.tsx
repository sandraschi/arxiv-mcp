import { useEffect, useState } from "react";
import { apiGet } from "@/api/client";
import { PageHero } from "@/components/layout/PageHero";
import { Card, CardTitle } from "@/components/ui/card";
import { useLogger } from "@/context/LoggerContext";

type Skill = { id: string; name: string; description: string; uri: string };

export function SkillsPage() {
  const { log } = useLogger();
  const [skills, setSkills] = useState<Skill[]>([]);

  useEffect(() => {
    (async () => {
      try {
        const d = await apiGet<{ skills: Skill[] }>("/api/skills");
        setSkills(d.skills);
      } catch (e) {
        log("error", String(e));
      }
    })();
  }, [log]);

  return (
    <div className="space-y-6">
      <PageHero
        eyebrow="MCP skills"
        title="Bundled skills"
        lead="Expert workflows exposed via skill:// resources when the MCP client supports skills."
      />
      <div className="grid gap-4 md:grid-cols-2">
        {skills.map((s) => (
          <Card key={s.id}>
            <CardTitle className="font-mono text-base">{s.name}</CardTitle>
            <p className="text-sm text-muted-foreground mt-2">
              {s.description}
            </p>
            <p className="text-xs font-mono text-primary mt-3">{s.uri}</p>
          </Card>
        ))}
        {skills.length === 0 && (
          <p className="text-sm text-muted-foreground">No skills registered.</p>
        )}
      </div>
    </div>
  );
}
