import type { AgentClient } from "../../api/agentClient";
import type { EventDetail } from "../../domain/apiTypes";
import { EventSelector } from "../event-selector/EventSelector";

interface MultiEventSelectorProps {
  client: AgentClient;
  selectedEvents: EventDetail[];
  locked: boolean;
  onChange: (events: EventDetail[]) => void;
}

export function MultiEventSelector(props: MultiEventSelectorProps) {
  return (
    <EventSelector
      mode="multi"
      client={props.client}
      selectedEvents={props.selectedEvents}
      disabled={props.locked}
      onChange={props.onChange}
    />
  );
}
