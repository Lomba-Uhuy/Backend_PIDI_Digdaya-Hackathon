import { HttpModule } from "@nestjs/axios";
import { Module } from "@nestjs/common";
import { AuthModule } from "../auth/auth.module.js";
import { AuthProxyController } from "./auth.proxy.js";
import { DealProxyController } from "./deal.proxy.js";
import { ActivityProxyController } from "./activity.proxy.js";
import { AiProxyController } from "./ai.proxy.js";
import { WorkflowProxyController } from "./workflow.proxy.js";
import { SubscriptionProxyController } from "./subscription.proxy.js";
import { PublicPlansProxyController } from "./public-plans.proxy.js";
import { AdminProxyController } from "./admin.proxy.js";
import { ReminderProxyController } from "./reminder.proxy.js";
import { MarketProxyController } from "./market.proxy.js";
import { DocumentProxyController } from "./document.proxy.js";
import { PublicReadinessProxyController } from "./public-readiness.proxy.js";
import { MatchingProxyController } from "./matching.proxy.js";
import { CommsProxyController } from "./comms.proxy.js";
import { ReadinessProxyController } from "./readiness.proxy.js";
import { UserProxyController } from "./user.proxy.js";

@Module({
  imports: [HttpModule, AuthModule],
  controllers: [
    AuthProxyController,
    DealProxyController,
    ActivityProxyController,
    AiProxyController,
    WorkflowProxyController,
    SubscriptionProxyController,
    PublicPlansProxyController,
    AdminProxyController,
    ReminderProxyController,
    MarketProxyController,
    UserProxyController,
    MatchingProxyController,
    CommsProxyController,
    PublicReadinessProxyController,
    DocumentProxyController,
    ReadinessProxyController,
  ],
})
export class ProxyModule {}
