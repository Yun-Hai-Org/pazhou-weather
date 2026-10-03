export class SlotStore {
  constructor(private readonly storage: DurableObjectStorage) {}

  async claim(date: string, slot: string, requestId: string): Promise<boolean> {
    const key = `slot:v2:${date}:${slot}`;
    return this.storage.transactionSync(() => {
      const state = this.storage.kv.get<{ status: string }>(key);
      if (state?.status === "sent") return false;
      this.storage.kv.put(`${key}:lease`, { requestId, at: Date.now() });
      return true;
    });
  }

  async release(date: string, slot: string, requestId?: string): Promise<void> {
    const key = `slot:v2:${date}:${slot}:lease`;
    if (!requestId) {
      await this.storage.delete(key);
      return;
    }
    await this.storage.transactionSync(() => {
      const lease = this.storage.kv.get<{ requestId: string }>(key);
      if (lease?.requestId === requestId) this.storage.kv.delete(key);
    });
  }

  async markSent(date: string, slot: string, deploymentId?: string): Promise<void> {
    await this.storage.put(`slot:v2:${date}:${slot}`, { status: "sent", deploymentId, at: Date.now() });
    await this.storage.delete(`slot:v2:${date}:${slot}:lease`);
  }
}
