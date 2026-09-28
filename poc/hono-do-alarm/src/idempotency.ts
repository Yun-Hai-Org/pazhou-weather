export class SlotStore {
  constructor(private readonly storage: DurableObjectStorage) {}

  async claim(date: string, slot: string, requestId: string): Promise<boolean> {
    const key = `slot:v2:${date}:${slot}`;
    const state = await this.storage.get<{ status: string }>(key);
    if (state?.status === "sent") return false;
    await this.storage.put(`${key}:lease`, { requestId, at: Date.now() });
    return true;
  }

  async release(date: string, slot: string): Promise<void> {
    await this.storage.delete(`slot:v2:${date}:${slot}:lease`);
  }

  async markSent(date: string, slot: string, deploymentId?: string): Promise<void> {
    await this.storage.put(`slot:v2:${date}:${slot}`, { status: "sent", deploymentId, at: Date.now() });
    await this.storage.delete(`slot:v2:${date}:${slot}:lease`);
  }
}
