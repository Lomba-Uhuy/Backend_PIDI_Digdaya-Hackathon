CREATE TYPE "public"."verification_status" AS ENUM('PENDING', 'IN_PROGRESS', 'VERIFIED', 'FAILED');--> statement-breakpoint
CREATE TABLE "umkm" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"legal_name" varchar(255) NOT NULL,
	"nib" varchar(13) NOT NULL,
	"description" text,
	"verification_status" "verification_status" DEFAULT 'PENDING' NOT NULL,
	"verified_score" numeric(5, 4) DEFAULT '0' NOT NULL,
	"oss_rba_data" jsonb DEFAULT '{}'::jsonb NOT NULL,
	"inatrade_data" jsonb DEFAULT '{}'::jsonb NOT NULL,
	"certifications" text[] DEFAULT '{}' NOT NULL,
	"user_id" uuid NOT NULL,
	"is_active" boolean DEFAULT true NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	CONSTRAINT "umkm_nib_unique" UNIQUE("nib")
);
--> statement-breakpoint
CREATE TABLE "product" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"umkm_id" uuid NOT NULL,
	"name" varchar(255) NOT NULL,
	"description" text NOT NULL,
	"hs_code" varchar(10),
	"hs_confidence" numeric(5, 4),
	"moq" integer DEFAULT 1 NOT NULL,
	"monthly_capacity" integer DEFAULT 0 NOT NULL,
	"price_min" numeric(18, 4) NOT NULL,
	"price_max" numeric(18, 4) NOT NULL,
	"hpp" numeric(18, 4) NOT NULL,
	"photo_urls" text[] DEFAULT '{}' NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "users" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"email" varchar(255) NOT NULL,
	"password_hash" varchar(255) NOT NULL,
	"tenant_id" uuid,
	"tier" varchar(16) DEFAULT 'free' NOT NULL,
	"is_active" boolean DEFAULT true NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	CONSTRAINT "users_email_unique" UNIQUE("email")
);
--> statement-breakpoint
ALTER TABLE "umkm" ADD CONSTRAINT "umkm_user_id_users_id_fk" FOREIGN KEY ("user_id") REFERENCES "public"."users"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "product" ADD CONSTRAINT "product_umkm_id_umkm_id_fk" FOREIGN KEY ("umkm_id") REFERENCES "public"."umkm"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
CREATE INDEX "umkm_nib_idx" ON "umkm" USING btree ("nib");--> statement-breakpoint
CREATE INDEX "umkm_user_id_idx" ON "umkm" USING btree ("user_id");--> statement-breakpoint
CREATE INDEX "umkm_verification_status_idx" ON "umkm" USING btree ("verification_status");--> statement-breakpoint
CREATE INDEX "product_umkm_idx" ON "product" USING btree ("umkm_id");--> statement-breakpoint
CREATE INDEX "product_hs_code_idx" ON "product" USING btree ("hs_code");