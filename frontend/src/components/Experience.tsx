import { useProfile } from "@/hooks/useProfile";
import ExperienceCard from "./ExperienceCard";

const Experience = () => {
  const { profile, loading, error } = useProfile();

  if (loading) {
    return (
      <section id="experience" className="py-24 px-6">
        <div className="max-w-4xl mx-auto text-center text-muted-foreground">
          Loading experience...
        </div>
      </section>
    );
  }

  if (error || !profile) {
    return (
      <section id="experience" className="py-24 px-6">
        <div className="max-w-4xl mx-auto text-center text-destructive">
          Failed to load experience data
        </div>
      </section>
    );
  }

  return (
    <section id="experience" className="py-24 px-6">
      <div className="max-w-4xl mx-auto">
        {/* Section header */}
        <div className="mb-12">
          <h2 className="text-4xl md:text-5xl font-serif text-foreground mb-4">
            Experience
          </h2>
          <p className="text-muted-foreground text-lg max-w-2xl">
            Each role includes queryable AI context—the real story behind the bullet points.
          </p>
        </div>

        {/* Experience cards */}
        <div className="space-y-6">
          {profile.experience?.map((exp, index) => (
            <ExperienceCard
              key={exp.company}
              {...exp}
              index={index}
            />
          ))}
        </div>

        {/* Skills Grid - only show if there's content */}
        {(profile.skills?.strong?.length > 0 ||
          profile.skills?.moderate?.length > 0 ||
          profile.skills?.gaps?.length > 0) && (
          <div className="mt-16 grid md:grid-cols-3 gap-6">
            {profile.skills?.strong?.length > 0 && (
              <div className="p-6 bg-success-muted border border-success/20 rounded-2xl">
                <h4 className="text-sm font-mono uppercase tracking-wider text-success mb-4">
                  Strong
                </h4>
                <ul className="space-y-2">
                  {profile.skills.strong.map((skill) => (
                    <li key={skill} className="text-foreground flex items-center gap-2">
                      <span className="text-success">✓</span>
                      {skill}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {profile.skills?.moderate?.length > 0 && (
              <div className="p-6 bg-secondary border border-border rounded-2xl">
                <h4 className="text-sm font-mono uppercase tracking-wider text-muted-foreground mb-4">
                  Moderate
                </h4>
                <ul className="space-y-2">
                  {profile.skills.moderate.map((skill) => (
                    <li key={skill} className="text-foreground flex items-center gap-2">
                      <span className="text-muted-foreground">○</span>
                      {skill}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {profile.skills?.gaps?.length > 0 && (
              <div className="p-6 bg-warning-muted border border-warning/20 rounded-2xl">
                <h4 className="text-sm font-mono uppercase tracking-wider text-warning mb-4">
                  Gaps (I'll tell you)
                </h4>
                <ul className="space-y-2">
                  {profile.skills.gaps.map((skill) => (
                    <li key={skill} className="text-foreground flex items-center gap-2">
                      <span className="text-warning">✗</span>
                      {skill}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </section>
  );
};

export default Experience;
