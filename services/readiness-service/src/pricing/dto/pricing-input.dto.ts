import { IsInt, IsNumber, Max, Min } from 'class-validator';

export class PricingInputDto {
  @IsNumber() @Min(0.01)
  hpp!: number;

  @IsNumber() @Min(0)
  originCharges!: number;

  @IsInt() @Min(1)
  qty!: number;

  @IsNumber() @Min(0)
  oceanFreight!: number;

  @IsNumber() @Min(0) @Max(1)
  insuranceRate!: number;
}