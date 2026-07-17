import { ApiPropertyOptional } from '@nestjs/swagger';
import { IsIn, IsNumber, IsOptional, IsString, Min } from 'class-validator';
import { DEAL_STATUSES } from './create-deal.dto.js';

export class UpdateDealDto {
  @ApiPropertyOptional({ enum: DEAL_STATUSES })
  @IsOptional()
  @IsIn(DEAL_STATUSES)
  status?: (typeof DEAL_STATUSES)[number];

  @ApiPropertyOptional({ example: 2.75, minimum: 0 })
  @IsOptional()
  @IsNumber()
  @Min(0)
  agreedPrice?: number;

  @ApiPropertyOptional({ example: 'Buyer menyetujui harga final.' })
  @IsOptional()
  @IsString()
  lastMessage?: string;
}
