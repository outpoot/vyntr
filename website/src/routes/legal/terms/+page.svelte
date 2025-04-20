<script lang="ts">
    import { Separator } from "$lib/components/ui/separator";
    import { Button } from "$lib/components/ui/button";
    import * as Card from "$lib/components/ui/card";
    import ScrollText from "lucide-svelte/icons/scroll-text";
    import { goto } from "$app/navigation";
    import { page } from "$app/state";

    const LAST_UPDATED = "April 20, 2025";
</script>

<svelte:head>
    <title>Terms of Service: Vyntr</title>
    <meta
        name="description"
        content="Read the terms of service of Vyntr, the privacy-focused search engine."
    />
    <meta name="keywords" content="terms, service, agreement, vyntr, search engine" />
    <meta property="og:title" content="Terms of Service: Vyntr" />
    <meta
        property="og:description"
        content="Read the terms of service of Vyntr, the privacy-focused search engine."
    />
    <meta property="og:type" content="website" />
    <meta property="og:url" content={page.url.href} />
</svelte:head>

<div class="container mx-auto max-w-4xl py-10">
    <Card.Root class="p-6">
        <div class="mb-8 flex items-center gap-3">
            <ScrollText class="h-10 w-10 text-primary" />
            <div>
                <h1 class="text-4xl font-bold">Terms of Service</h1>
                <p class="text-muted-foreground">
                    Last updated: {LAST_UPDATED}
                </p>
            </div>
        </div>

        <Separator class="my-6" />

        <div class="space-y-8">
            <Card.Content>
                <h2 class="mb-4 text-2xl font-semibold">1. Acceptance of Terms</h2>
                <p class="mb-4">By accessing or using Vyntr's search engine and related services, you agree to be bound by these Terms of Service. If you disagree with any part of these terms, you may not access our services.</p>
                <p>These terms apply to all users, whether using our free services or premium features. Users must be at least 13 years of age to access our services. If you are under 13, please do not use Vyntr.</p>
            </Card.Content>

            <Card.Content>
                <h2 class="mb-4 text-2xl font-semibold">2. Service Description</h2>
                <p class="mb-4">Vyntr provides a search engine that allows users to search the internet. Our core search functionality is provided free of charge, with optional premium features available through paid subscriptions.</p>
                <p class="mb-4">We cannot guarantee the completeness or accuracy of any information found through our service. Search results are sourced from public web content and may include AI-generated summaries to enhance user experience.</p>
                <p>Our service includes features such as:</p>
                <ul class="ml-6 mt-2 list-disc space-y-2 marker:text-primary">
                    <li>Web search</li>
                    <li>AI-powered search summaries</li>
                    <li>Optional account features</li>
                    <li>API access (subject to terms)</li>
                </ul>
            </Card.Content>

            <Card.Content>
                <h2 class="mb-4 text-2xl font-semibold">3. User Responsibilities</h2>
                <p class="mb-4">When using Vyntr's services, you agree to:</p>
                <div class="space-y-4">
                    <div>
                        <h3 class="mb-2 text-lg font-medium">3.1 Acceptable Use</h3>
                        <p class="mb-2">Users must use our services in compliance with all applicable laws and regulations. You are responsible for all activity conducted through your account and must not:</p>
                        <ul class="ml-6 list-disc space-y-2 marker:text-primary">
                            <p class="mt-4">Engage in any automated scraping or data collection without explicit permission</p>
                            <p>Attempt to circumvent our rate limiting or security measures</p>
                            <p>Use our services to distribute malware or harmful content</p>
                            <p>Interfere with other users' access to the service</p>
                        </ul>
                    </div>

                    <div>
                        <h3 class="mb-2 text-lg font-medium">3.2 Account Security</h3>
                        <p>If you create an account, you are responsible for maintaining the confidentiality of your account credentials and for all activities that occur under your account. Notify us immediately of any unauthorized use or security breach.</p>
                    </div>
                </div>
            </Card.Content>

            <Card.Content>
                <h2 class="mb-4 text-2xl font-semibold">4. Premium Services</h2>
                <p class="mb-4">Vyntr offers premium features through paid subscriptions powered by Polar. By subscribing to our premium services:</p>
                <div class="space-y-4">
                    <p>Your subscription and payments are managed securely through our payment provider, Polar. All billing-related matters, including fees, refunds, and subscription management, are handled according to Polar's terms of service.</p>
                    <p>We reserve the right to modify premium features with reasonable notice. Any changes will be communicated to subscribers before taking effect.</p>
                </div>
            </Card.Content>

            <Card.Content>
                <h2 class="mb-4 text-2xl font-semibold">5. Privacy & Data</h2>
                <ul class="ml-6 list-disc space-y-2 marker:text-primary">
                    <li>Details outlined in our <a href="/legal/privacy" class="text-primary hover:underline">Privacy Policy</a></li>
                    <li>Optional anonymous usage analytics</li>
                    <li>Search history is not stored</li>
                    <li>Data deletion available through account settings</li>
                </ul>
            </Card.Content>

            <Card.Content>
                <h2 class="mb-4 text-2xl font-semibold">6. Yappatron AI</h2>
                <ul class="ml-6 list-disc space-y-2 marker:text-primary">
                    <li>AI responses may be inaccurate or incomplete</li>
                    <li>Usage limits apply based on account type</li>
                    <li>AI content should not be used for critical decisions</li>
                    <li>Responses may use various information sources</li>
                </ul>
            </Card.Content>

            <Card.Content>
                <h2 class="mb-4 text-2xl font-semibold">7. Website Registry</h2>
                <ul class="ml-6 list-disc space-y-2 marker:text-primary">
                    <li>Website submissions subject to verification</li>
                    <li>Submitted content must be lawful and appropriate</li>
                    <li>We reserve the right to remove listings</li>
                    <li>Voting and interaction limits may apply</li>
                </ul>
            </Card.Content>

            <Card.Content>
                <h2 class="mb-4 text-2xl font-semibold">8. Liability</h2>
                <ul class="ml-6 list-disc space-y-2 marker:text-primary">
                    <li>Service provided "as is" without warranties</li>
                    <li>No liability for service interruptions</li>
                    <li>User responsible for search result usage</li>
                    <li>API usage at user's own risk</li>
                </ul>
            </Card.Content>

            <Card.Content>
                <h2 class="mb-4 text-2xl font-semibold">9. Changes to Terms</h2>
                <p class="mb-4">We reserve the right to modify these terms at any time. We will provide notice of significant changes through our website or via email if you have an account. Your continued use of Vyntr after such modifications constitutes acceptance of the updated terms.</p>
                <p>We encourage you to review these terms periodically for any changes. If you disagree with the modified terms, you should discontinue using our services.</p>
            </Card.Content>

            <div class="text-sm text-muted-foreground">
                <p>Last Updated: {LAST_UPDATED}</p>
            </div>
        </div>

        <Separator class="my-8" />

        <div class="flex justify-center">
            <Button
                variant="outline"
                size="lg"
                onclick={() => goto("/legal/privacy")}
            >
                Read our Privacy Policy →
            </Button>
        </div>
    </Card.Root>
</div>