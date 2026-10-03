import './HelpCard.css';

interface HelpCardProps {
    title: string;
    items: string[];
    note?: string;
}

export default function HelpCard({title, items, note}: HelpCardProps) {
    return <div className="help-card">
        <strong className="help-card-title">{title}</strong>
        <ul className="help-card-list">{items.map((item, index) => <li key={index}>{item}</li>)}</ul>
        {note && <div className="help-card-note">{note}</div>}
    </div>;
}
