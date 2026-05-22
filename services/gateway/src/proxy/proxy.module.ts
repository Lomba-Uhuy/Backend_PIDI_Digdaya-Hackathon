import { HttpModule } from '@nestjs/axios';
import { Module } from '@nestjs/common';
import { AuthModule } from '../auth/auth.module.js';
import { MatchingProxyController } from './matching.proxy.js';
import { CommsProxyController } from './comms.proxy.js';
import { ReadinessProxyController } from './readiness.proxy.js';
import { UserProxyController } from './user.proxy.js';

@Module({
  imports: [HttpModule, AuthModule],
  controllers: [
    UserProxyController,
    MatchingProxyController,
    CommsProxyController,
    ReadinessProxyController,
  ],
})
export class ProxyModule {}