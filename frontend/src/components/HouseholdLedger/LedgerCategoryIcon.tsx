import {BedDouble, BriefcaseBusiness, Bus, CircleDollarSign, HeartPulse, Landmark, Package, ShoppingBag, ShoppingBasket, Ticket, TrendingUp, Utensils, WalletCards} from 'lucide-react';

const categoryIcons = {
    1: Utensils, 2: Bus, 3: BedDouble, 4: Ticket, 5: ShoppingBag, 6: WalletCards,
    7: BriefcaseBusiness, 8: BriefcaseBusiness, 9: TrendingUp, 10: Landmark,
    11: CircleDollarSign, 12: ShoppingBasket, 13: HeartPulse,
};

export default function LedgerCategoryIcon({category}: {category: number}) {
    const Icon = categoryIcons[category as keyof typeof categoryIcons] || Package;
    return <span className="ledger-category-icon"><Icon size={17} strokeWidth={1.7} aria-hidden="true"/></span>;
}
