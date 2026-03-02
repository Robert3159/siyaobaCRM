declare namespace Api {
  namespace Notification {
    interface Message {
      id: string;
      player_id?: number;
      submitter: string;
      country?: string;
      age?: string;
      server?: string;
      token?: string;
      summary?: string;
      created_at: string;
    }
  }
}
